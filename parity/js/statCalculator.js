let unitData,  // global variables containing properly formatted game data.
    modSetData,
    gearData,
    crTables,
    gpTables,
    relicData;

module.exports = {
  setGameData: (gameData) => {
    unitData = gameData.unitData;
    gearData = gameData.gearData;
    modSetData = gameData.modSetData;
    crTables = gameData.crTables;
    gpTables = gameData.gpTables;
    relicData = gameData.relicData;
  },
  calcCharStats: calcCharStats,
  calcShipStats: calcShipStats,
  calcRosterStats: calcRosterStats,
  calcPlayerStats: (players, options) => {
    if (Array.isArray(players)) { // full profile array from /player
      let count = 0;
      for (const player of players) {
        count += calcRosterStats(player.roster || player.rosterUnit, options);
      }
      return count;
    } else { // single player object
      return calcRosterStats(players.roster || players.rosterUnit, options);
    }
  },
  calcCharGP: ( char, options = {} ) => {
    char = useValuesChar(char, options.useValues);
    return calcCharGP( char );
  },
  calcShipGP: ( ship, crew, options = {} ) => {
    ({ship, crew} = useValuesShip(ship, crew, options.useValues));
    for (const c of crew) c.gp = calcCharGP( c );
    return calcShipGP( ship, crew );
  }
}

const DEFAULT_MOD_TIER = 5;
const DEFAULT_MOD_LEVEL = 15;
const DEFAULT_MOD_PIPS = 6;

// Helper to safely extract a unit's definition ID
function getDefId(unit) {
  return unit && (unit.defId || (unit.definitionId && unit.definitionId.split(':')[0])) || undefined;
}

function calcRosterStats(units, options = {}) {
  let count = 0;
  if (Array.isArray(units)) { // units formatted like /player.roster
    const ships = [];
    const crew = Object.create(null);
    // get character stats
    for (const unit of units) {
      const defID = getDefId(unit);
      if (!defID) continue;
      const meta = unitData[defID];
      if (!meta) continue;
      if (meta.combatType == 2) { // is ship
        ships.push(unit);
      } else { // is character
        crew[defID] = unit; // add to crew list to find quickly for ships
        calcCharStats(unit, options);
      }
    }
    // get ship stats
    for (const ship of ships) {
      const defID = getDefId(ship);
      if (!defID) continue;
      const meta = unitData[defID];
      if (!meta) continue;
      const crw = meta.crew.map(id => crew[id]).filter(Boolean);
      calcShipStats(ship, crw, options);
    }
    count += units.length;
  } else { // units formatted like /units or /roster
    for (const id of Object.keys(units)) {
      const list = units[id];
      const isChar = unitData[id] && unitData[id].combatType == 1;
      if (!isChar) continue;
      for (const unit of list) {
        const tempUnit = {
          defId: id,
          rarity: unit.starLevel,
          level: unit.level,
          gear: unit.gearLevel,
          equipped: (unit.gear || []).map(gearID => ({ equipmentId: gearID })),
          mods: unit.mods
        };
        calcCharStats(tempUnit, options);
        // assign modified values from calcCharStats back to the original units
        if (tempUnit.stats) unit.stats = tempUnit.stats;
        if (tempUnit.gp) unit.gp = tempUnit.gp;
        count++;
      }
    }
  }
  return count;
}

function calcCharStats(unit, options = {}) {
  let char = useValuesChar(unit, options.useValues);

  let stats = {};
  if (!options.onlyGP) {
    stats = getCharRawStats(char);
    stats = calculateBaseStats(stats, char.level, char.defId);
    if (!options.withoutModCalc) { stats.mods = calculateModStats(stats.base, char); }
    stats = formatStats(stats, char.level, options);
    stats = renameStats(stats, options);

    unit.stats = stats;
  }

  if (options.calcGP || options.onlyGP) {
    unit.gp = calcCharGP(char);
    stats.gp = unit.gp;
  }

  return stats;
}

function calcShipStats(unit, crewMember, options = {}) {
  try {
    let {ship, crew} = useValuesShip(unit, crewMember, options.useValues);

    let stats = {};
    if (!options.onlyGP) {
      stats = getShipRawStats(ship, crew);
      stats = calculateBaseStats(stats, ship.level, ship.defId);
      stats = formatStats(stats, ship.level, options);
      stats = renameStats(stats, options);

      unit.stats = stats;
    }

    if (options.calcGP || options.onlyGP) {
      unit.gp = calcShipGP(ship, crew);
      stats.gp = unit.gp;
    }

    return stats;
  } catch(e) {
    console.error(`Error on ship '${ship.defId}':\n${JSON.stringify(ship)}`);
    console.error(e.stack);
    throw e;
  }
}



function getCharRawStats(char) {
  const meta = unitData[char.defId];
  const stats = {
    base: { ...meta.gearLvl[char.gear].stats },
    growthModifiers: { ...meta.growthModifiers[char.rarity] },
    gear: Object.create(null)
  };
  const base = stats.base;
  const gearAgg = stats.gear;
  // calculate stats from current gear:
  for (const gearPiece of char.equipped) {
    const gearEntry = gearData[gearPiece.equipmentId];
    if (!gearEntry) continue; // Unknown gear -- no stats
    const gearStats = gearEntry.stats;
    for (const statID in gearStats) {
      const value = gearStats[statID];
      if (statID == 2 || statID == 3 || statID == 4) {
        // Primary Stat, applies before mods
        base[statID] = (base[statID] || 0) + value;
      } else {
        // Secondary Stat, applies after mods
        gearAgg[statID] = (gearAgg[statID] || 0) + value;
      }
    }
  }
  if (char.relic && char.relic.currentTier > 2) {
    // calculate stats from relics
    const relic = relicData[ meta.relic[ char.relic.currentTier ] ];
    for (const statID in relic.stats) {
      base[ statID ] = (base[ statID ] || 0) + relic.stats[ statID ];
    }
    for (const statID in relic.gms) {
      stats.growthModifiers[ statID ] += relic.gms[ statID ];
    }
  }
  return stats;
}
function getShipRawStats(ship, crew) {
  const meta = unitData[ship.defId];
  // ensure crew is the correct crew
  if (crew.length != meta.crew.length)
    throw new Error(`Incorrect number of crew members for ship ${ship.defId}.`);
  for (const char of crew) {
    if (!meta.crew.includes(char.defId))
      throw new Error(`Unit ${char.defId} is not in ${ship.defId}'s crew.`);
  }
  // if still here, crew is good -- go ahead and determine stats
  const crewRating = crew.length == 0 ? getCrewlessCrewRating(ship) : getCrewRating(crew);
  const stats = {
    base: { ...meta.stats },
    crew: Object.create(null),
    growthModifiers: { ...meta.growthModifiers[ship.rarity] }
  };
  const statMultiplier = crTables.shipRarityFactor[ship.rarity] * crewRating;
  for (const statID in meta.crewStats) {
    const statValue = meta.crewStats[statID];
    // stats 1-15 and 28 all have final integer values
    // other stats require decimals -- shrink to 8 digits of precision through 'unscaled' values this calculator uses
    stats.crew[statID] = floor(statValue * statMultiplier, (statID < 16 || statID == 28) ? 8 : 0);
  }
  return stats;
}

function getCrewRating(crew) {
  let totalCR = crew.reduce( (crewRating, char) => {
    crewRating += crTables.unitLevelCR[ char.level ] + crTables.crewRarityCR[ char.rarity ]; // add CR from level/rarity
    crewRating += crTables.gearLevelCR[ char.gear ]; // add CR from complete gear levels
    crewRating += (crTables.gearPieceCR[ char.gear ] * char.equipped.length || 0); // add CR from currently equipped gear
    crewRating = char.skills.reduce( (cr, skill) => cr + getSkillCrewRating(skill), crewRating); // add CR from ability levels
     // add CR from mods
    if (char.mods) crewRating = char.mods.reduce( (cr, mod) => cr + crTables.modRarityLevelCR[ mod.pips ][ mod.level ], crewRating);
    else if (char.equippedStatMod) crewRating = char.equippedStatMod.reduce( (cr, mod) => cr + crTables.modRarityLevelCR[ +mod.definitionId[1] ][ mod.level ], crewRating);

    // add CR from relics
    if (char.relic && char.relic.currentTier > 2) {
      crewRating += crTables.relicTierCR[ char.relic.currentTier ];
      crewRating += char.level * crTables.relicTierLevelFactor[ char.relic.currentTier ];
    }

    return crewRating;
  }, 0);
  return totalCR;
}
function getSkillCrewRating(skill) {
  // Crew Rating for GP purposes depends on skill type (i.e. contract/hardware/etc.), but for stats it apparently doesn't.
  return crTables.abilityLevelCR[ skill.tier ];
}

function getCrewlessCrewRating(ship) {
  // temporarily uses hard-coded multipliers, as the true in-game formula remains a mystery.
  // but these values have experimentally been found accurate for the first 3 crewless ships:
  //     (Vulture Droid, Hyena Bomber, and BTL-B Y-wing)
  return floor( crTables.crewRarityCR[ ship.rarity ] + 3.5*crTables.unitLevelCR[ ship.level ] + getCrewlessSkillsCrewRating( ship.skills ) );
}
function getCrewlessSkillsCrewRating(skills) {
  return skills.reduce( (cr, skill) => {
    cr += ((skill.id.substring(0,8) == "hardware") ? 0.696 : 2.46) * crTables.abilityLevelCR[ skill.tier ];
    return cr;
  }, 0);
}

/* Return object structure:
  {
    base: { statID: statValue, ...},
    gear: { statID: statValue, ...},
    growthModifiers: { 2: STR_GM, 3: AGI_GM, 4: TAC_GM }
  }
*/
function calculateBaseStats(stats, level, baseID) {
  // calculate bonus Primary stats from Growth Modifiers:
  stats.base[2] += floor(stats.growthModifiers[2] * level, 8); // Strength
  stats.base[3] += floor(stats.growthModifiers[3] * level, 8); // Agility
  stats.base[4] += floor(stats.growthModifiers[4] * level, 8); // Tactics

  const ud = unitData[baseID];
  if (stats.base[61]) {
    // calculate effects of Mastery on Secondary stats:
    const mms = crTables[ud.masteryModifierID];
    for (const statID in mms) {
      stats.base[statID] = (stats.base[statID] || 0) + stats.base[61] * mms[statID];
    }
  }
  // calculate effects of Primary stats on Secondary stats:
  stats.base[1] = (stats.base[1] || 0) + stats.base[2] * 18;                                            // Health += STR * 18
  stats.base[6] = floor((stats.base[6] || 0) + stats.base[ud.primaryStat] * 1.4, 8); // Ph. Damage += MainStat * 1.4
  stats.base[7] = floor((stats.base[7] || 0) + (stats.base[4] * 2.4), 8);                               // Sp. Damage += TAC * 2.4
  stats.base[8] = floor((stats.base[8] || 0) + (stats.base[2] * 0.14) + (stats.base[3] * 0.07), 8);      // Armor += STR*0.14 + AGI*0.07
  stats.base[9] = floor((stats.base[9] || 0) + (stats.base[4] * 0.1), 8);                                // Resistance += TAC * 0.1
  stats.base[14] = floor((stats.base[14] || 0) + (stats.base[3] * 0.4), 8);                              // Ph. Crit += AGI * 0.4
  // add hard-coded minimums or potentially missing stats
  stats.base[12] = (stats.base[12] || 0) + (24 * 1e8);  // Dodge (24 -> 2%)
  stats.base[13] = (stats.base[13] || 0) + (24 * 1e8);  // Deflection (24 -> 2%)
  stats.base[15] = (stats.base[15] || 0);               // Sp. Crit
  stats.base[16] = (stats.base[16] || 0) + (150 * 1e6); // +150% Crit Damage
  stats.base[18] = (stats.base[18] || 0) + (15 * 1e6);  // +15% Tenacity

  return stats;
}


/* Return object structure:
  { statID: statValue, ...}

  Input 'char.mods' structures (.help formats):
    /units format:
  [ {
      set: number,
      level: number,
      stat: [ [ statID, statVal ],  <- Primary Stat
              [ statID, statVal ],  <- Secondary 1
              [ statID, statVal ],  <- Secondary 2
              [ statID, statVal ],  <- Secondary 3
              [ statID, statVal ] ] <- Secondary 4
      // missing secondaries have statID and statVal set to 0
    },
    // missing mods are empty objects
    ... ]
    /player.roster format:
  [ {
      set: number,
      level: number,
      primaryStat: { unitStat: number,
                     value: number },
      secondaryStat: [
        { unitStat: number,
          value: number },
        ... ]
      // missing secondaries don't exist in list
    },
    // missing mods don't exist in list
    ... ]

  Input 'char.equippedStatMod' structure (raw format)
  [ {
      definitionId: string, // three digits, first is set ID
      level: number,
      parimaryStat: { unitStatId: number,
                      unscaledDecimalValue: string/number },
      secondaryStat: [
        { unitStatId, number,
          unscaledDecimalValue: string/number },
        ... ]
      // missing secondaries don't exist in list
    },
    // missing mods don't exist in list
    ... ]
*/
function calculateModStats(baseStats, char) {
  // return empty object if no mods
  if ( !char.mods && !char.equippedStatMod ) return {};

  // calculate raw totals on mods
  const setBonuses = {};
  const rawModStats = {};
  if (char.mods) {
    char.mods.forEach(mod => {
      if (!mod.set) { return; } // ignore if empty mod (/units format only)

      // add to set bonuses counters (same for both formats)
      if (setBonuses[ mod.set ]) {
        // set bonus already found, increment
        ++(setBonuses[ mod.set ].count);
        if (mod.level == 15) ++(setBonuses[mod.set].maxLevel);
      } else {
        // new set bonus, create object
        setBonuses[ mod.set ] = { count: 1, maxLevel: mod.level == 15 ? 1 : 0 };
      }

      // add Primary/Secondary stats to data
      if (mod.stat) {
        // using /units format
        mod.stat.forEach( stat => {
          rawModStats[ stat[0] ] = (rawModStats[ stat[0] ] || 0) + scaleStatValue(stat[0], stat[1]);
        });
      } else {
        // using /player.roster format
        let stat = mod.primaryStat,
            i = 0;
        do {
          rawModStats[ stat.unitStat ] = (rawModStats[ stat.unitStat ] || 0) + scaleStatValue(stat.unitStat, stat.value);
          stat = mod.secondaryStat[i];
        } while ( i++ < mod.secondaryStat.length );
      }

      function scaleStatValue(statID, value) {
        // convert stat value from displayed value to "unscaled" value used in calculations
        switch (statID) {
          case 1:  // Health
          case 5:  // Speed
          case 28: // Protection
          case 41: // Offense
          case 42: // Defense
            // Flat stats
            return value * 1e8;
          default:
            // Percent stats
            return value * 1e6;
        }
      }
    });
  } else if (char.equippedStatMod) {
    char.equippedStatMod.forEach( mod => {
      let setBonus;
      if ( setBonus = setBonuses[ +mod.definitionId[0] ] ) {
        // set bonus already found, increment
        ++setBonus.count;
        if ( mod.level == 15 ) ++setBonus.maxLevel;
      } else {
        // new set bonus, create object
        setBonuses[ +mod.definitionId[0] ] = { count: 1, maxLevel: mod.level == 15 ? 1 : 0 };
      }

      // add Primary/Secondary stats to data
      let stat = mod.primaryStat.stat, i = 0;
      do {
        rawModStats[ stat.unitStatId ] = +stat.unscaledDecimalValue + (rawModStats[ stat.unitStatId ] || 0);
        stat = mod.secondaryStat[i] && mod.secondaryStat[i].stat;
      } while ( i++ < mod.secondaryStat.length );
    });
  } else {
    // return empty object if no mods
    return {};
  }

  // add stats given by set bonuses
  for (var setID in setBonuses) {
    const setDef = modSetData[setID];
    const {count: count, maxLevel: maxCount } = setBonuses[ setID ];
    const multiplier = ~~(count / setDef.count) + ~~(maxCount / setDef.count);
    rawModStats[ setDef.id ] = (rawModStats[ setDef.id ] || 0) + (setDef.value * multiplier);
  }

  // calcuate actual stat bonuses from mods
  const modStats = {};
  for (var statID in rawModStats) {
    const value = rawModStats[ statID ];
    switch (~~statID) {
      case 41: // Offense
        modStats[6] = (modStats[6] || 0) + value; // Ph. Damage
        modStats[7] = (modStats[7] || 0) + value; // Sp. Damage
        break;
      case 42: // Defense
        modStats[8] = (modStats[8] || 0) + value; // Armor
        modStats[9] = (modStats[9] || 0) + value; // Resistance
        break;
      case 48: // Offense %
        modStats[6] = floor( (modStats[6] || 0) + (baseStats[6] * 1e-8 * value), 8); // Ph. Damage
        modStats[7] = floor( (modStats[7] || 0) + (baseStats[7] * 1e-8 * value), 8); // Sp. Damage
        break;
      case 49: // Defense %
        modStats[8] = floor( (modStats[8] || 0) + (baseStats[8] * 1e-8 * value), 8); // Armor
        modStats[9] = floor( (modStats[9] || 0) + (baseStats[9] * 1e-8 * value), 8); // Resistance
        break;
      case 53: // Crit Chance
        modStats[21] = (modStats[21] || 0) + value; // Ph. Crit Chance
        modStats[22] = (modStats[22] || 0) + value; // Sp. Crit Chance
        break;
      case 54: // Crit Avoid
        modStats[35] = (modStats[35] || 0) + value; // Ph. Crit Avoid
        modStats[36] = (modStats[36] || 0) + value; // Ph. Crit Avoid
        break;
      case 55: // Heatlth %
        modStats[1] = floor( (modStats[1] || 0) + (baseStats[1] * 1e-8 * value), 8); // Health
        break;
      case 56: // Protection %
        modStats[28] = floor( (modStats[28] || 0) + ( (baseStats[28] || 0) * 1e-8 * value), 8); // Protection may not exist in base
        break;
      case 57: // Speed %
        modStats[5] = floor( (modStats[5] || 0) + (baseStats[5] * 1e-8 * value), 8); // Speed
        break;
      default:
        // other stats add like flat values
        modStats[ statID ] = (modStats[ statID ] || 0) + value;
    }
  }

  return modStats;
}


// Apply following flags to adjust object format
//   -scaled
//   -unscaled
//   -gameStyle
//   -percentVals
function formatStats(stats, level, options) {
  // value/scaling flags
  let scale = 1; // also useful in some Stat Format calculations below

  if (options.scaled) { scale = 1e-4; }
  else if (!options.unscaled) { scale = 1e-8; }

  if (stats.mods) {
    for (var statID in stats.mods) stats.mods[statID] = Math.round( stats.mods[statID] );
  }

  if (scale != 1) {
    for (var statID in stats.base) stats.base[statID] *= scale;
    for (var statID in stats.gear) stats.gear[statID] *= scale;
    for (var statID in stats.crew) stats.crew[statID] *= scale;
    for (var statID in stats.growthModifiers) stats.growthModifiers[statID] *= scale;
    if (stats.mods) {
      for (var statID in stats.mods) stats.mods[statID] *= scale;
    }
  }

  if (options.percentVals || options.gameStyle) { // 'gameStyle' flag inherently includes 'percentVals'
    let vals;
    // convert Crit
    convertPercent(14, val => convertFlatCritToPercent( val, scale * 1e8 ) ); // Ph. Crit Rating -> Chance
    convertPercent(15, val => convertFlatCritToPercent( val, scale * 1e8 ) ); // Sp. Crit Rating -> Chance
    // convert Def
    convertPercent(8, val => convertFlatDefToPercent( val, level, scale * 1e8, stats.crew ? true:false ) ); // Armor
    convertPercent(9, val => convertFlatDefToPercent( val, level, scale * 1e8, stats.crew ? true:false ) ); // Resistance
    // convert Acc
    convertPercent(37, val => convertFlatAccToPercent( val, scale * 1e8 ) ); // Physical Accuracy
    convertPercent(38, val => convertFlatAccToPercent( val, scale * 1e8 ) ); // Special Accuracy
    // convert Evasion
    convertPercent(12, val => convertFlatAccToPercent( val, scale * 1e8 ) ); // Dodge
    convertPercent(13, val => convertFlatAccToPercent( val, scale * 1e8 ) ); // Deflection
    // convert Crit Avoidance
    convertPercent(39, val => convertFlatCritAvoidToPercent( val, scale * 1e8 ) ); // Physical Crit Avoidance
    convertPercent(40, val => convertFlatCritAvoidToPercent( val, scale * 1e8 ) ); // Special Crit Avoidance

    // calls 'convertFunc' for all stat values of 'statID' in stats, and replaces those values with the % granted by that stat type
    //   i.e. mods = convertFunc(base + gear + mods) - convertFunc(base + gear)
    //     or for ships: crew = convertFunc(base + crew) - convertFunc(crew)
    function convertPercent(statID, convertFunc) {
      let flat = stats.base[statID],
          percent = convertFunc(flat);
      stats.base[statID] = percent;
      let last = percent;
      if (stats.crew) { // is Ship
        if (stats.crew[statID]) {
          stats.crew[statID] = (/*percent = */convertFunc(flat += stats.crew[statID])) - last;
        }
      } else { // is Char
        if (stats.gear && stats.gear[statID]) {
          stats.gear[statID] = (percent = convertFunc(flat += stats.gear[statID])) - last;
          last = percent;
        }
        if (stats.mods && stats.mods[statID]) stats.mods[statID] = (/*percent = */convertFunc(flat += stats.mods[statID])) - last;
      }
    }
  }

  if (options.gameStyle) {
    let gsStats = { final:{} };
    // get list of all stat IDs used in base
    const statList = Object.keys(stats.base);
    const addStats = statID => { if (!statList.includes(statID)) statList.push(statID); }
    if (stats.gear) { // is Char
      Object.keys(stats.gear).forEach(addStats); // add stats from gear to list
      if (stats.mods) Object.keys(stats.mods).forEach(addStats); // add stats from mods to list
      if (stats.mods) gsStats.mods = stats.mods; // keep mod stats untouched

      statList.forEach( statID => {
        let flatStatID = statID;
        switch (~~statID) {
            // stats with both Percent Stats get added to the ID for their flat stat (which was converted to % above)
          case 21: // Ph. Crit Chance
          case 22: // Sp. Crit Chance
            flatStatID = statID - 7; // 21-14 = 7 = 22-15 ==> subtracting 7 from statID gets the correct flat stat
            break;
          case 35: // Ph. Crit Avoid
          case 36: // Sp. Crit Avoid
            flatStatID = ~~statID + 4; // 39-35 = 4 = 40-36 ==> adding 4 to statID gets the correct flat stat
            break;
          default:
        }
        gsStats.final[flatStatID] = gsStats.final[flatStatID] || 0; // ensure stat already exists
        gsStats.final[flatStatID] += (stats.base[statID] || 0) + (stats.gear[statID] || 0) + (stats.mods && stats.mods[statID] ? stats.mods[statID] : 0);
      });

    } else { // is Ship
      Object.keys(stats.crew).forEach(addStats); // add stats from crew to list
      gsStats.crew = stats.crew; // keep crew stats untouched

      statList.forEach( statID => {
        gsStats.final[statID] = (stats.base[statID] || 0) + (stats.crew[statID] || 0);
      });
    }

    stats = gsStats;
  }

  return stats;
}


// rename object keys based on language
//   -language (indexed object/array with strings for each stat)
//   -noSpace (true/false)
function renameStats(stats, options) {
  if (options.language) {
    const rnStats = {};
    Object.keys(stats).forEach( statType => {
      rnStats[ statType ] = {}
      Object.keys( stats[ statType ] ).forEach( statID => {
        let statName = options.language[ statID ] || statID; // leave as statID if no localization string is found
        if (options.noSpace) {
          statName = statName.replace(/\s/g, ''); // remove spaces
          statName = statName[0].toLowerCase() + statName.slice(1); // ensure first letter is lower case
        }
        rnStats[ statType ][ statName ] = stats[ statType ][ statID ];
      });
    });
    stats = rnStats;
  }
  return stats;
}






// *****************************
// ****** GP Calculations ******
// *****************************

function calcCharGP(char) {
  let gp = gpTables.unitLevelGP[ char.level ];
  gp += gpTables.unitRarityGP[ char.rarity ];
  gp += gpTables.gearLevelGP[ char.gear ];
  // Game tables for current gear include the possibility of differect GP per slot.
  // Currently, all values are identical across each gear level, so a simpler method is possible.
  // But that could change at any time.
  gp = char.equipped.reduce( (power, piece) => power + gpTables.gearPieceGP[ char.gear ][ piece.slot ], gp);
  gp = char.skills.reduce( (power, skill) => power + getSkillGP(char.defId, skill), gp);
  if (char.purchasedAbilityId) gp += char.purchasedAbilityId.length * gpTables.abilitySpecialGP.ultimate;
  if (char.mods) gp = char.mods.reduce( (power, mod) => power + gpTables.modRarityLevelTierGP[ mod.pips ][ mod.level ][ mod.tier ], gp);
  else if (char.equippedStatMod) gp = char.equippedStatMod.reduce( (power, mod) => power + gpTables.modRarityLevelTierGP[ +mod.definitionId[1] ][ mod.level ][ mod.tier ], gp)

  if (char.relic && char.relic.currentTier > 2) {
    gp += gpTables.relicTierGP[ char.relic.currentTier ];
    gp += char.level * gpTables.relicTierLevelFactor[ char.relic.currentTier ];
  }
  return floor( gp*1.5 );
}
function getSkillGP(id, skill) {
  let oTag = unitData[ id ].skills.find( s => s.id == skill.id ).powerOverrideTags[ skill.tier ];
  if (oTag)
    return gpTables.abilitySpecialGP[ oTag ];
  else
    return gpTables.abilityLevelGP[ skill.tier ] || 0;
}
function calcShipGP(ship, crew = []) {
  // ensure crew is the correct crew
  if (crew.length != unitData[ship.defId].crew.length)
    throw new Error(`Incorrect number of crew members for ship ${ship.defId}.`);
  crew.forEach( char => {
    if ( !unitData[ship.defId].crew.includes(char.defId) )
      throw new Error(`Unit ${char.defId} is not in ${ship.defId}'s crew.`);
  });

  let gp;

  if (crew.length == 0) { // crewless calculations
    let gps = getCrewlessSkillsGP( ship.defId, ship.skills );
    gps.level = gpTables.unitLevelGP[ ship.level ];
    gp = ( gps.level*3.5 + gps.ability*5.74 + gps.reinforcement*1.61 )*gpTables.shipRarityFactor[ ship.rarity ];
    gp += gps.level + gps.ability + gps.reinforcement;
  } else { // normal ship calculations
    gp = crew.reduce( (power, c) => power + c.gp, 0);
    gp *= gpTables.shipRarityFactor[ ship.rarity ] * gpTables.crewSizeFactor[ crew.length ]; // multiply crewPower factors before adding other GP sources
    gp += gpTables.unitLevelGP[ ship.level ];
    gp = ship.skills.reduce( (power, skill) => power + getSkillGP(ship.defId, skill), gp);
  }
  return floor( gp*1.5 );
}
function getCrewlessSkillsGP(id, skills) {
  let a = 0,
      r = 0;
  skills.forEach( skill => {
    let oTag = unitData[ id ].skills.find( s => s.id == skill.id ).powerOverrideTags[ skill.tier ];
    if (oTag && oTag.substring(0,13) == 'reinforcement')
      r += gpTables.abilitySpecialGP[ oTag ];
    else
      a += oTag ? gpTables.abilitySpecialGP[ oTag ] : gpTables.abilityLevelGP[ skill.tier ];
  });

  return {ability: a, reinforcement: r};
}




// ******************************
// ****** Helper Functions ******
// ******************************

// correct round-off error inherit to floats
function fixFloat(value,digits) {
  return Number(`${Math.round(`${value}e${digits}`)}e-${digits}`) || 0;
}

// floor value to specified digit
function floor(value, digits = 0) {
  return Math.floor(value / ('1e'+digits)) * ('1e'+digits);
}


// convert def
function convertFlatDefToPercent(value, level = 85, scale = 1, isShip = false) {
  const val = value / scale;
  const level_effect = isShip ? 300 + level*5 : level*7.5;
  return (val/(level_effect + val)) * scale;//.toFixed(2);
}

// convert crit
function convertFlatCritToPercent(value, scale = 1) {
  const val = value / scale;
  return (val/2400 + 0.1) * scale;//.toFixed(4);
}

// convert accuracy / evasion
function convertFlatAccToPercent(value, scale = 1) {
  const val = value / scale;
  return (val/1200) * scale;
}

// convert crit avoidance
function convertFlatCritAvoidToPercent(value, scale = 1) {
  const val = value / scale;
  return (val/2400) * scale;
}


// build character from 'useValues' option
function useValuesChar(char, useValues) {
  if ( !char.defId ) char = {
    defId: char.definitionId.split(":")[0],
    rarity: char.currentRarity,
    level: char.currentLevel,
    gear: char.currentTier,
    equipped: char.equipment,
    equippedStatMod: char.equippedStatMod,
    relic: char.relic,
    skills: char.skill.map( skill => { return { id: skill.id, tier: skill.tier + 2 }; })
    // TODO set purchasedAbilityId
  };
  if (!useValues) return char;

  let unit = {
    defId: char.defId,
    rarity: useValues.char.rarity || char.rarity,
    level: useValues.char.level || char.level,
    gear: useValues.char.gear || char.gear,
    equipped: char.gear,
    mods: char.mods,
    equippedStatMod: char.equippedStatMod,
    relic: useValues.char.relic ? {currentTier: useValues.char.relic } : char.relic,
    skills: setSkills(char.defId, useValues.char.skills || char.skills || [])
    // TODO set purchasedAbilityId
  };

  if (useValues.char.modRarity || useValues.char.modLevel || useValues.char.modTier) {
    unit.mods = [];
    for (let i=0; i<6; i++) {
      unit.mods.push({
        pips: useValues.char.modRarity || DEFAULT_MOD_PIPS,
        level: useValues.char.modLevel || DEFAULT_MOD_LEVEL,
        tier: useValues.char.modTier || DEFAULT_MOD_TIER
      });
    }
  }

  if (useValues.char.equipped == "all") {
    unit.equipped = [];
    unitData[ unit.defId ].gearLvl[ unit.gear ].gear.forEach( gearID => {
      if (+gearID < 9990) // gear IDs 9998 or 9999 are currently used for 'unknown' gear.  Highest valid gear ID through gear level 12+5 is 173.
        unit.equipped.push( { equipmentId: gearID } );
    });
  } else if (useValues.char.equipped == "none") {
    unit.equipped = [];
  } else if (useValues.char.equipped.constructor === Array) { // expecting array of gear slots
    unit.equipped = useValues.char.equipped.map( slot => {
      return unitData[ unit.defId ].gearLvl[ unit.gear].gear[ +slot - 1 ];
    });
  }

  return unit;
}

// build ship/crew from 'useValues' option
function useValuesShip(ship, crew, useValues) {
  if ( !ship.defId ) {
    ship = {
      defId: ship.definitionId.split(":")[0],
      rarity: ship.currentRarity,
      level: ship.currentLevel,
      skills: ship.skill.map( skill => { return { id: skill.id, tier: skill.tier + 2 }; })
    };
    crew = crew.map( c => {
      return {
        defId: c.definitionId.split(":")[0],
        rarity: c.currentRarity,
        level: c.currentLevel,
        gear: c.currentTier,
        equipped: c.equipment,
        equippedStatMod: c.equippedStatMod,
        relic: c.relic,
        skills: c.skill.map( skill => { return { id: skill.id, tier: skill.tier + 2 }; }),
        gp: c.gp
      };
    });
  }
  if (!useValues) return {ship: ship, crew: crew};

  ship = {
    defId: ship.defId,
    rarity: useValues.ship.rarity || ship.rarity,
    level: useValues.ship.level || ship.level,
    skills: setSkills(ship.defId, useValues.ship.skills || ship.skills)
  }

  let chars = unitData[ ship.defId ].crew.map( charID => {
    let char = crew.find( cmem => { return cmem.defId == charID} ); // extract defaults from submitted crew
    char = {
      defId: charID,
      rarity: useValues.crew.rarity || char.rarity,
      level: useValues.crew.level || char.level,
      gear: useValues.crew.gear || char.gear,
      equipped: char.gear,
      skills: setSkills(charID, useValues.crew.skills || char.skills),
      mods: char.mods,
      relic: useValues.crew.relic ? {currentTier: useValues.crew.relic } : char.relic
    };

    if (useValues.crew.equipped == "all") {
      char.equipped = [];
      unitData[ charID ].gearLvl[ char.gear ].gear.forEach( gearID => {
        if (+gearID < 9990) // gear IDs 9998 or 9999 are currently used for 'unknown' gear.  Highest valid gear ID through gear level 12+5 is 173.
          char.equipped.push( { equipmentId: gearID } );
      });
    } else if (useValues.crew.equipped == "none") {
      char.equipped = [];
    } else if (useValues.crew.equipped.constructor === Array) { // expecting array of gear slots
      char.equipped = useValues.char.equipped.map( slot => {
        return unitData[ charID ].gearLvl[ char.gear].gear[ +slot - 1 ];
      });
    } else if (useValues.crew.equipped) { // expecting an integer, 1-6, for number of gear slots filled (specific gear pieces don't actually matter for ships)
      char.equipped = [];
      for (let i=0; i<useValues.crew.equipped; i++)
        char.equipped.push({});
    }

    if (useValues.crew.modRarity || useValues.crew.modLevel) {
      char.mods = [];
      for (let i=0; i<6; i++) {
        char.mods.push({
          pips: useValues.crew.modRarity || DEFAULT_MOD_PIPS,
          level: useValues.crew.modLevel || DEFAULT_MOD_LEVEL,
          tier: useValues.crew.modTier || DEFAULT_MOD_TIER
        });
      }
    }

    return char;
  });

  return {ship: ship, crew: chars};

}

function setSkills( unitID, val ) {
  if (val == 'max')
    return unitData[ unitID ].skills.map(skill => { return {id: skill.id, tier: skill.maxTier}; });
  else if (val == 'maxNoZeta')
    return unitData[ unitID ].skills.map(skill => { return {id: skill.id, tier: skill.maxTier - (skill.isZeta ? 1 : 0)}; });
  else if ('number' == typeof val) // expecting an integer, 1-8, for skill level to use
    return unitData[ unitID ].skills.map(skill => { return {id: skill.id, tier: Math.min(val, skill.maxTier)}; });
  else // expecting an array of skill objects
    return val;
}

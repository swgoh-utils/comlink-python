const fs = require('fs');
const path = require('path');

function usage() {
  console.error('Usage: node run_js_player_parity.js <gameData.json> <player.json>');
  process.exit(2);
}

if (process.argv.length < 4) {
  usage();
}

const gameDataPath = process.argv[2];
const playerPath = process.argv[3];

const calc = require(path.join(__dirname, '..', 'js', 'statCalculator.js'));
const gameData = JSON.parse(fs.readFileSync(gameDataPath, 'utf-8'));
const player = JSON.parse(fs.readFileSync(playerPath, 'utf-8'));

calc.setGameData(gameData);

const fixedOptions = {
  calcGP: true,
  gameStyle: true,
  percentVals: true,
};

function getDefId(unit) {
  return (unit.definitionId || '').split(':')[0];
}

function sanitizePlayer(input) {
  const payload = JSON.parse(JSON.stringify(input));
  const roster = Array.isArray(payload.rosterUnit) ? payload.rosterUnit : [];
  payload.rosterUnit = roster.filter((unit) => {
    const defId = getDefId(unit);
    const meta = gameData.unitData[defId];
    if (!meta) return false;

    if (unit.relic && unit.relic.currentTier > 2) {
      const relicMap = meta.relic || [];
      let maxRelicTier;
      if (Array.isArray(relicMap)) {
        maxRelicTier = relicMap.length - 1;
      } else {
        const keys = Object.keys(relicMap)
          .map((k) => Number(k))
          .filter((n) => Number.isFinite(n));
        maxRelicTier = keys.length ? Math.max(...keys) : -1;
      }
      if (maxRelicTier < 3) {
        unit.relic.currentTier = 2;
      } else if (unit.relic.currentTier > maxRelicTier) {
        unit.relic.currentTier = maxRelicTier;
      }
      const relicDef = relicMap[String(unit.relic.currentTier)] ?? relicMap[unit.relic.currentTier];
      if (!relicDef || !gameData.relicData[String(relicDef)]) {
        unit.relic.currentTier = 2;
      }
    }

    const skillDefs = Array.isArray(meta.skills) ? meta.skills : [];
    const skillById = new Map(skillDefs.map((s) => [s.id, s]));
    const skills = Array.isArray(unit.skill) ? unit.skill : [];
    unit.skill = skills
      .filter((s) => skillById.has(s.id))
      .map((s) => {
        const def = skillById.get(s.id);
        const maxTier = def && Number.isFinite(def.maxTier) ? def.maxTier : s.tier;
        const next = { ...s };
        if (next.tier > maxTier) next.tier = maxTier;
        if (next.tier < 1) next.tier = 1;
        return next;
      });

    return true;
  });
  return payload;
}

const payload = sanitizePlayer(player);
const count = calc.calcPlayerStats(payload, fixedOptions);

process.stdout.write(JSON.stringify({ count, player: payload }));

const fs = require('fs');
const path = require('path');

function usage() {
  console.error('Usage: node run_js_parity.js <gameData.json> <fixtures.json>');
  process.exit(2);
}

if (process.argv.length < 4) {
  usage();
}

const gameDataPath = process.argv[2];
const fixturesPath = process.argv[3];

const calc = require(path.join(__dirname, '..', 'js', 'statCalculator.js'));
const gameData = JSON.parse(fs.readFileSync(gameDataPath, 'utf-8'));
const fixtures = JSON.parse(fs.readFileSync(fixturesPath, 'utf-8'));

calc.setGameData(gameData);
const fixedOptions = {
  calcGP: true,
  gameStyle: true,
  percentVals: true,
};

function clone(obj) {
  return JSON.parse(JSON.stringify(obj));
}

const charUnit = clone(fixtures.char);
const charStats = calc.calcCharStats(charUnit, fixedOptions);

const crewUnits = clone(fixtures.crew);
for (const c of crewUnits) {
  c.gp = calc.calcCharGP(c);
}
const shipUnit = clone(fixtures.ship);
const shipStats = calc.calcShipStats(shipUnit, crewUnits, fixedOptions);

const roster = clone(fixtures.roster);
const rosterCount = calc.calcRosterStats(roster, fixedOptions);

const players = clone(fixtures.players);
const playerCount = calc.calcPlayerStats(players, fixedOptions);

const payload = {
  char: {
    stats: charStats,
    gp: charUnit.gp,
    unit: charUnit,
  },
  ship: {
    stats: shipStats,
    gp: shipUnit.gp,
    unit: shipUnit,
    crew: crewUnits,
  },
  roster: {
    count: rosterCount,
    units: roster,
  },
  players: {
    count: playerCount,
    players,
  },
};

process.stdout.write(JSON.stringify(payload));

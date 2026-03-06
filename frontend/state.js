var State = {
  user: null,
  run: null,
  todayStatus: null,
  catchup: null,
  inventory: [],
  garage: { cars: [], cosmetics: [], activeCarId: null },
  profile: null,
  activeScene: 'run',
};

function setState(partial) {
  Object.assign(State, partial);
}

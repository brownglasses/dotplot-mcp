// 가짜 음악 앱 코드 — audit_tracking 시연용
function onPlaySong(song) {
  startPlayback(song);
  logEvent("play_song");
}

function onSearch(query) {
  showResults(search(query));
  logEvent("search");
}

function onCreatePlaylist(name) {
  db.createPlaylist(name);
  logEvent("create_playlist");
}

function onShareSong(song) {
  openShareSheet(song);
  logEvent("share_song"); // 심어져 있음 — 근데 데이터에 한 번도 안 찍힘 (버그? 아무도 안 씀?)
}

function onFollowArtist(artist) {
  db.follow(artist);
  // 로깅 없음! ← 중요한 행동인데 추적 구멍
}

function onAppOpen() {
  logEvent("open_app");
}

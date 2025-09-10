// Minimal UI scaffold; real-time streaming to be added.
(function () {
  const log = document.getElementById('log');
  function append(line) {
    const div = document.createElement('div');
    div.className = 'entry';
    div.textContent = line;
    log.appendChild(div);
  }
  append('Ready. This UI will show streamed updates once the backend is wired.');
})();


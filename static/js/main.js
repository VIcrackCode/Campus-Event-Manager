// Live password strength validation
const pwd = document.getElementById('password');
const hint = document.getElementById('pwdHint');
if (pwd && hint) {
  const re = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&#])[A-Za-z\d@$!%*?&#]{8,}$/;
  pwd.addEventListener('input', () => {
    const v = pwd.value;
    if (!v) { hint.textContent=''; return; }
    if (re.test(v)) { hint.textContent='Strong password'; hint.style.color='#16a34a'; }
    else { hint.textContent='Needs 8+ chars, upper, lower, number & special'; hint.style.color='#dc2626'; }
  });
}

// Auto-dismiss alerts
setTimeout(() => {
  document.querySelectorAll('.alert').forEach(a => {
    try { bootstrap.Alert.getOrCreateInstance(a).close(); } catch(e){}
  });
}, 5000);

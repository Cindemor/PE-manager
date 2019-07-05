function StuManagement(id) {
    document.getElementById('operationintroduction').classList.add('hide');
    document.getElementById('operation').classList.remove('hide');
    var mode = document.getElementById('mode');
    mode.value = id;
}
function aftersubmit() {
    document.getElementById('operation').classList.add('hide');
    document.getElementById('operationintroduction').classList.remove('hide');
}
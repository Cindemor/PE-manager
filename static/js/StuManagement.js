function StuManagement(id) {
    document.getElementById('operationintroduction').classList.add('hide');
    document.getElementById('operation').classList.remove('hide');
    var mode = document.getElementById('mode');
    mode.value = id;
}
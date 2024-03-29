from flask import render_template, Flask, views, request, redirect, session, send_from_directory, make_response, send_file
from DBUtils.PooledDB import PooledDB
from flask_wtf.csrf import CsrfProtect
import pymysql
import tablib
from datetime import timedelta

app = Flask(__name__)
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = timedelta(seconds = 0)
app.secret_key = "secret_key"
CsrfProtect(app)

POOL = PooledDB(
    creator = pymysql,
    host = "127.0.0.1",
    port = 3306,
    user = "root",
    password = "zq",
    database = "PE_management",
    charset = "utf8"
)

class m_data():
    def __init__(self, list):
        self.__list = list
    def get_list(self):
        return self.__list

class stu_data(m_data):
    def __init__(self, sno, sname, term, cname, grade, list):
        self.__sno = sno
        self.__sname = sname
        self.__term = term
        self.__cname = cname
        self.__grade = grade
        self.__list = list
    def get_sno(self):
        return self.__sno
    def get_sname(self):
        return self.__sname
    def get_term(self):
        return self.__term
    def get_cname(self):
        return self.__cname
    def get_grade(self):
        return self.__grade
    def get_list(self):
        return self.__list

class login_view(views.View):
    def __init__(self):
        self.db = POOL.connection()
        self.cursor = self.db.cursor()
        self.valid_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_.?~+=@%$&^*:0123456789')

    def input_valid(self, words):
        for i in words:
            if i not in self.valid_chars:
                return False
        return True

    def make_msg(self, err):
        if err == "1":
            msg = "用户名或密码不正确"
        code = """
        <script>
            window.onload = function() {
                alert('""" + msg + """')
            }
        </script>
        """
        return code

    def dispatch_request(self):
        if request.method == "POST":
            username = request.form.get("account")
            password = request.form.get("password")
            remember = request.form.get("remember")
            if self.input_valid(username) and self.input_valid(password):
                #输入合法
                self.cursor.execute("select username from user where username = '" + username + "' and password = '" + password + "'")
                login_user = self.cursor.fetchone()
                if login_user:
                    #登录成功
                    session["user"] = login_user[0]
                    if remember and remember == "on":
                        session.permanent = True
                    return redirect("/")
                else:
                    return redirect("/login?err=1")
            else:
                return redirect("/login?err=1")
        else:
            if session.get('user'):
                #已登录
                return redirect("/")
            else:
                err = request.args.get("err")
                if err:
                    return render_template("login.html", msg = self.make_msg(err))
                else:
                    return render_template("login.html")

    def __del__(self):
        self.cursor.close()
        self.db.close()


class index_view(views.View):
    def __init__(self):
        self.db = POOL.connection()
        self.cursor = self.db.cursor()
        self.project_no = {
            "50m": "001",
            "push": "002",
            "jump": "003",
            "rise": "004",
            "up": "005",
            "1000/800m": "006",
            "rope": "007",
            "2400/2000m": "008",
            "app": "009",
            "write": "010",
            "sign": "011",
            "special": "012"
        }
        self.project_na = {
            "50m": "50米",
            "push": "坐位体前屈",
            "jump": "立定跳远",
            "rise": "引体向上",
            "up": "仰卧起坐",
            "1000/800m": "1000米/800米",
            "rope": "跳绳",
            "2400/2000m": "2400米/2000米",
            "app": "运动世界校园",
            "write": "理论作业",
            "sign": "考勤",
            "special": "专项"
        }
        self.project_un = {
            "001" : "秒",
            "002" : "厘米",
            "003" : "厘米",
            "004": "个",
            "005": "个",
            "006": "分/秒",
            "007": "个",
            "008": "分/秒",
            "009": "",
            "010": "",
            "011": "",
            "012": ""
        }

    def input_valid(self, words):
        if "'" in words:
            return False
        return True

    def show_record(self, pno, record, unit):
        if pno == "006" or pno == "008":
            res = record.replace('.', '\'')
        else:
            res = record + unit
        return res

    def super_cal(self, pno, record, gender):
        self.cursor.execute("select record_level, score_level from standard where Pno = '" + pno + "' and gender = '" + gender + "' and record_level >= '" + record + "' order by record_level limit 1 offset 0")
        up = self.cursor.fetchone()
        self.cursor.execute("select record_level, score_level from standard where Pno = '" + pno + "' and gender = '" + gender + "' and record_level <= '" + record + "' order by record_level desc limit 1 offset 0")
        down = self.cursor.fetchone()
        if pno == '001' or pno == '006' or pno == '008':
            up, down = down, up
        if up[0]:
            up_r = up[0]
        else:
            return "100"
        if down[0]:
            down_r = down[0]
        else:
            return "0"
        up_s = up[1]
        down_s = down[1]
        if up_r - down_r:
            rate = (float(record) - down_r) / (up_r - down_r)
        else:
            rate = 0
        score = '%(p).2f' % {'p': down_s + ((up_s - down_s) * rate)}
        return score

    def make_msg(self, err):
        if err == "1":
            msg = "用户名或密码不正确"
        elif err == "2":
            msg = "非法输入"
        elif err == "3":
            msg = "任意一项内容均不能为空"
        elif err == "4":
            msg = "学号已存在"
        elif err == "5":
            msg = "学号不存在"
        elif err == "6":
            msg = "学号不能为空"
        elif err == "7":
            msg = "课程号已存在"
        elif err == "8":
            msg = "课程号不存在"
        elif err == "9":
            msg = "课程号不能为空"
        elif err == "10":
            msg = "教工号已存在"
        elif err == "11":
            msg = "教工号不存在"
        elif err == "12":
            msg = "教工号不能为空"
        elif err == "13":
            msg = "用户不存在"
        elif err == "14":
            msg = "两次输入的密码不一致"
        code = """
        <script>
            window.onload = function() {
                alert('""" + msg + """')
            }
        </script>
        """
        return code

    def dispatch_request(self):
        if not session.get('user'):
            #未登录
            return redirect("/login")
        username = session.get('user')
        self.cursor.execute("select role from user where username = '" + username + "'")
        login_role = self.cursor.fetchone()
        if login_role:
            #存在角色
            role = login_role[0]
            if role == 'student':
                #学生页面
                self.cursor.execute("select Sno, Sname, Term, Sclass, Sgrade from student where Sno = '" + username + "'")
                login_info = self.cursor.fetchone()
                sno = login_info[0]
                sname = login_info[1]
                term = login_info[2]
                cno = login_info[3]
                grade = login_info[4]
                if not grade:
                    #无成绩
                    grade = "暂无"
                self.cursor.execute("select Cname from course where Cno = '" + cno + "'")
                cname = self.cursor.fetchone()[0]
                self.cursor.execute("select Pro_Record, Pro_Unit, Pro_Score, pname, sp.pno from sp join project where sp.Sno = '" + username + "' and sp.Pno = project.Pno")
                rows = self.cursor.fetchall()
                pro_list = []
                for row in rows:
                    if not row[2]:
                        continue
                    temp = {}
                    temp["pname"] = self.project_na[row[3]]
                    temp["grade"] = row[2]
                    pno = row[4]
                    unit = row[1]
                    record = row[0]
                    if record:
                        record = self.show_record(pno, record, unit)
                    else:
                        record = "无"
                    temp["record"] = record
                    pro_list.append(temp)
                data = stu_data(sno, sname, term, cname, grade, pro_list)
                return render_template("Student.html", data = data)
            elif role == 'admin':
                #管理员页面
                action = request.args.get("action")
                if not action:
                    return redirect("/?action=sm")
                elif action == "sm":
                    #学生管理
                    if request.method == "GET":
                        self.cursor.execute("select Sno, Sname, Sgender, Term, Sclass from student")
                        rows = self.cursor.fetchall()
                        sm_list = []
                        for row in rows:
                            temp = {}
                            temp["sno"] = row[0]
                            temp["name"] = row[1]
                            temp["gender"] = row[2]
                            temp["term"] = row[3]
                            temp["class"] = row[4]
                            sm_list.append(temp)
                        data = m_data(sm_list)
                        err = request.args.get("err")
                        if err:
                            return render_template("StuManagement.html", data = data, msg = self.make_msg(err))
                        else:
                            return render_template("StuManagement.html", data = data)
                    else:
                        sno = request.form.get("sno")
                        name = request.form.get("name")
                        gender = request.form.get("gender")
                        term = request.form.get("term")
                        classno = request.form.get("class")
                        mode = request.form.get("mode")
                        if mode == "add":
                            #添加学生
                            if sno and name and gender and term and classno:
                                #不可为空
                                if self.input_valid(sno) and self.input_valid(name) and self.input_valid(gender) and self.input_valid(term) and self.input_valid(classno):
                                    #输入合法
                                    self.cursor.execute("select Cno from course where Cno = '" + classno + "'")
                                    cno = self.cursor.fetchone()
                                    self.cursor.execute("select Sno from student where Sno = '" + sno + "'")
                                    sno1 = self.cursor.fetchone()
                                    if sno1:
                                        return redirect("/?action=sm&err=4")
                                    if not cno:
                                        return redirect("/?action=sm&err=8")
                                    try:
                                        self.cursor.execute("insert into student values('" + sno + "', '" + name + "', '" + gender + "', '" + term + "', '" + classno + "', NULL)")
                                        self.db.commit()
                                    except:
                                        self.db.rollback()
                                    try:
                                        self.cursor.execute("insert into user values('" + sno + "', '" + sno + "', 'student')")
                                        self.db.commit()
                                    except:
                                        self.db.rollback()
                                    for k, v in self.project_un.items():
                                        try:
                                            self.cursor.execute("insert into sp (Sno, Pno, Pro_Unit) values('" + sno + "', '" + k + "', '" + v + "');")
                                            self.db.commit()
                                        except:
                                            self.db.rollback()
                                    return redirect("/?action=sm")
                                else:
                                    return redirect("/?action=sm&err=2")
                            else:
                                return redirect("/?action=sm&err=3")
                        elif mode == "delete":
                            #删除学生
                            if sno:
                                #学号不可为空
                                if self.input_valid(sno):
                                    #输入合法
                                    self.cursor.execute("select Sno from student where Sno = '" + sno + "'")
                                    sno1 = self.cursor.fetchone()
                                    if not sno1:
                                        return redirect("/?action=sm&err=5")
                                    try:
                                        self.cursor.execute("delete from sp where Sno = '" + sno + "'")
                                        self.db.commit()
                                    except:
                                        self.db.rollback()
                                    try:
                                        self.cursor.execute("delete from student where sno = '" + sno + "'")
                                        self.db.commit()
                                    except:
                                        self.db.rollback()
                                    try:
                                        self.cursor.execute("delete from user where username = '" + sno + "'")
                                        self.db.commit()
                                    except:
                                        self.db.rollback()
                                    return redirect("/?action=sm")
                                else:
                                    return redirect("/?action=sm&err=2")
                            else:
                                return redirect("/?action=sm&err=6")
                        elif mode == "update":
                            #更新学生信息
                            if sno:
                                #学号不可为空
                                if self.input_valid(sno) and self.input_valid(term) and self.input_valid(classno):
                                    #输入合法
                                    self.cursor.execute("select Sno from student where Sno = '" + sno + "'")
                                    sno1 = self.cursor.fetchone()
                                    if not sno1:
                                        return redirect("/?action=sm&err=5")
                                    if term:
                                        try:
                                            self.cursor.execute("update student set Term = '" + term + "' where Sno = '" + sno + "'")
                                            self.db.commit()
                                        except:
                                            self.db.rollback()
                                    if classno:
                                        self.cursor.execute("select Cno from course where Cno = '" + classno + "'")
                                        cno = self.cursor.fetchone()
                                        if not cno:
                                            return redirect("/?action=sm&err=8")
                                        try:
                                            self.cursor.execute("update student set Sclass = '" + classno + "' where Sno = '" + sno + "'")
                                            self.db.commit()
                                        except:
                                            self.db.rollback()
                                    return redirect("/?action=sm")
                                else:
                                    return redirect("/?action=sm&err=2")
                            else:
                                return redirect("/?action=sm&err=6")
                        elif mode == "search":
                            #查询学生信息
                            sql = "select Sno, Sname, Sgender, Term, Sclass from student where '1' = '1'"
                            if self.input_valid(sno) and self.input_valid(name) and self.input_valid(gender) and self.input_valid(term) and self.input_valid(classno):
                                #输入合法
                                if sno:
                                    sql += " and Sno = '" + sno + "'"
                                if name:
                                    sql += " and Sname = '" + name + "'"
                                if gender:
                                    sql += " and Sgender = '" + gender + "'"
                                if term:
                                    sql += " and Term = '" + term + "'"
                                if classno:
                                    sql += " and Sclass = '" + classno + "'"
                                self.cursor.execute(sql)
                                rows = self.cursor.fetchall()
                                sm_list = []
                                for row in rows:
                                    temp = {}
                                    temp["sno"] = row[0]
                                    temp["name"] = row[1]
                                    temp["gender"] = row[2]
                                    temp["term"] = row[3]
                                    temp["class"] = row[4]
                                    sm_list.append(temp)
                                data = m_data(sm_list)
                                return render_template("StuManagement.html", data = data)
                            else:
                                return redirect("/?action=sm&err=2")
                elif action == "tm":
                    #教师管理
                    if request.method == "GET":
                        self.cursor.execute("select Tno, Tname, Tgender, Tclass, Cname from teacher left join course on teacher.Tclass = course.cno")
                        rows = self.cursor.fetchall()
                        tm_list = []
                        for row in rows:
                            temp = {}
                            temp["tno"] = row[0]
                            temp["name"] = row[1]
                            temp["gender"] = row[2]
                            temp["class"] = row[3]
                            temp["cname"] = row[4]
                            if not row[4]:
                                temp["cname"] = ""
                            tm_list.append(temp)
                        data = m_data(tm_list)
                        err = request.args.get("err")
                        if err:
                            return render_template("TeaManagement.html", data = data, msg = self.make_msg(err))
                        else:
                            return render_template("TeaManagement.html", data = data)
                    else:
                        tno = request.form.get("tno")
                        name = request.form.get("name")
                        gender = request.form.get("gender")
                        classno = request.form.get("class")
                        mode = request.form.get("mode")
                        if mode == "add":
                            #添加教师
                            if tno and name and gender and  classno:
                                #不可为空
                                if self.input_valid(tno) and self.input_valid(name) and self.input_valid(gender) and self.input_valid(classno):
                                    #输入合法
                                    self.cursor.execute("select Cno from course where Cno = '" + classno + "'")
                                    cno1 = self.cursor.fetchone()
                                    self.cursor.execute("select Tno from teacher where Tno = '" + tno + "'")
                                    tno1 = self.cursor.fetchone()
                                    if tno1:
                                        return redirect("/?action=tm&err=10")
                                    if not cno1:
                                        return redirect("/?action=tm&err=8")
                                    try:
                                        self.cursor.execute("insert into teacher values('" + tno + "', '" + name + "', '" + gender + "', '" + classno + "')")
                                        self.db.commit()
                                    except:
                                        self.db.rollback()
                                    try:
                                        self.cursor.execute("insert into user values('" + tno + "', '" + tno + "', 'teacher')")
                                        self.db.commit()
                                    except:
                                        self.db.rollback()
                                    return redirect("/?action=tm")
                                else:
                                    return redirect("/?action=tm&err=2")
                            else:
                                return redirect("/?action=tm&err=3")
                        elif mode == "delete":
                            #删除教师
                            if tno:
                                #教工号不可为空
                                if self.input_valid(tno):
                                    #输入合法
                                    self.cursor.execute("select Tno from teacher where Tno = '" + tno + "'")
                                    tno1 = self.cursor.fetchone()
                                    if not tno1:
                                        return redirect("/?action=tm&err=11")
                                    try:
                                        self.cursor.execute("delete from teacher where Tno = '" + tno + "'")
                                        self.db.commit()
                                    except:
                                        self.db.rollback()
                                    try:
                                        self.cursor.execute("delete from user where username = '" + tno + "'")
                                        self.db.commit()
                                    except:
                                        self.db.rollback()
                                    return redirect("/?action=tm")
                                else:
                                    return redirect("/?action=tm&err=2")
                            else:
                                return redirect("/?action=tm&err=12")
                        elif mode == "update":
                            #更新教师信息
                            if tno:
                                #教工号不可为空
                                if self.input_valid(tno) and self.input_valid(classno):
                                    #输入合法
                                    self.cursor.execute("select Tno from teacher where Tno = '" + tno + "'")
                                    tno1 = self.cursor.fetchone()
                                    if not tno1:
                                        return redirect("/?action=tm&err=11")
                                    if classno:
                                        self.cursor.execute("select Cno from course where Cno = '" + classno + "'")
                                        cno = self.cursor.fetchone()
                                        if not cno:
                                            return redirect("/?action=tm&err=8")
                                        try:
                                            self.cursor.execute("update teacher set Tclass = '" + classno + "' where Tno = '" + tno + "'")
                                            self.db.commit()
                                        except:
                                            self.db.rollback()
                                    return redirect("/?action=tm")
                                else:
                                    return redirect("/?action=tm&err=2")
                            else:
                                return redirect("/?action=tm&err=12")
                        elif mode == "search":
                            #查询教师信息
                            sql = "select Tno, Tname, Tgender, Tclass, Cname from teacher left join course on teacher.Tclass = course.cno where '1' = '1'"
                            if self.input_valid(tno) and self.input_valid(name) and self.input_valid(gender) and self.input_valid(classno):
                                #输入合法
                                if tno:
                                    sql += " and Tno = '" + tno + "'"
                                if name:
                                    sql += " and Tname = '" + name + "'"
                                if gender:
                                    sql += " and Tgender = '" + gender + "'"
                                if classno:
                                    sql += " and Tclass = '" + classno + "'"
                                self.cursor.execute(sql)
                                rows = self.cursor.fetchall()
                                print (rows)
                                tm_list = []
                                for row in rows:
                                    temp = {}
                                    temp["tno"] = row[0]
                                    temp["name"] = row[1]
                                    temp["gender"] = row[2]
                                    temp["class"] = row[3]
                                    temp["cname"] = row[4]
                                    if not row[4]:
                                        temp["cname"] = ""
                                    tm_list.append(temp)
                                data = m_data(tm_list)
                                return render_template("TeaManagement.html", data = data)
                            else:
                                return redirect("/?action=tm&err=2")
                elif action == "cm":
                    #课程管理
                    if request.method == "GET":
                        self.cursor.execute("select Cno, Cname from course")
                        rows = self.cursor.fetchall()
                        cm_list = []
                        for row in rows:
                            temp = {}
                            temp["cno"] = row[0]
                            temp["cname"] = row[1]
                            self.cursor.execute("select Tname from teacher where Tclass = '" + row[0] + "'")
                            courses = self.cursor.fetchall()
                            teachers = ""
                            has_tea = False
                            for tea in courses:
                                if has_tea:
                                    #教师名枚举
                                    teachers += ("、" + tea[0])
                                else:
                                    has_tea = True
                                    teachers += tea[0]
                            temp["teachers"] = teachers
                            cm_list.append(temp)
                        data = m_data(cm_list)
                        err = request.args.get("err")
                        if err:
                            return render_template("CouManagement.html", data = data, msg = self.make_msg(err))
                        else:
                            return render_template("CouManagement.html", data = data)
                    else:
                        cno = request.form.get("cno")
                        cname = request.form.get("cname")
                        mode = request.form.get("mode")
                        if mode == "add":
                            #添加课程
                            if cno and cname:
                                #不可为空
                                if self.input_valid(cno) and self.input_valid(cname):
                                    #输入合法
                                    self.cursor.execute("select Cno from course where Cno = '" + cno + "'")
                                    cno1 = self.cursor.fetchone()
                                    if cno1:
                                        return redirect("/?action=cm&err=7")
                                    try:
                                        self.cursor.execute("insert into course values('" + cno + "', '" + cname + "')")
                                        self.db.commit()
                                    except:
                                        self.db.rollback()
                                    return redirect("/?action=cm")
                                else:
                                    return redirect("/?action=cm&err=2")
                            else:
                                return redirect("/?action=cm&err=3")
                        elif mode == "delete":
                            #删除课程
                            if cno:
                                #课程号不可为空
                                if self.input_valid(cno):
                                    #输入合法
                                    self.cursor.execute("select Cno from course where Cno = '" + cno + "'")
                                    cno1 = self.cursor.fetchone()
                                    if not cno1:
                                        return redirect("/?action=cm&err=8")
                                    try:
                                        self.cursor.execute("update student set Sclass = '' where Sclass = '" + cno + "'")
                                        self.db.commit()
                                    except:
                                        self.db.rollback()
                                    try:
                                        self.cursor.execute("update teacher set Tclass = '' where Tclass = '" + cno + "'")
                                        self.db.commit()
                                    except:
                                        self.db.rollback()
                                    try:
                                        self.cursor.execute("delete from course where cno = '" + cno + "'")
                                        self.db.commit()
                                    except:
                                        self.db.rollback()
                                    return redirect("/?action=cm")
                                else:
                                    return redirect("/?action=cm&err=2")
                            else:
                                return redirect("/?action=cm&err=9")
                        elif mode == "search":
                            #查询课程信息
                            sql = "select Cno, Cname from course where '1' = '1'"
                            if self.input_valid(cno) and self.input_valid(cname):
                                #输入合法
                                if cno:
                                    sql += " and Cno = '" + cno + "'"
                                if cname:
                                    sql += " and Cname = '" +cname + "'"
                                self.cursor.execute(sql)
                                rows = self.cursor.fetchall()
                                cm_list = []
                                for row in rows:
                                    temp = {}
                                    temp["cno"] = row[0]
                                    temp["cname"] = row[1]
                                    self.cursor.execute("select Tname from teacher where Tclass = '" + row[0] + "'")
                                    courses = self.cursor.fetchall()
                                    teachers = ""
                                    has_tea = False
                                    for tea in courses:
                                        if has_tea:
                                            #教师名枚举
                                            teachers += ("、" + tea[0])
                                        else:
                                            has_tea = True
                                            teachers += tea[0]
                                    temp["teachers"] = teachers
                                    cm_list.append(temp)
                                data = m_data(cm_list)
                                return render_template("CouManagement.html", data = data)
                            else:
                                return redirect("/?action=cm&err=2")
                elif action == "um":
                    #用户管理
                    if request.method == "GET":
                        self.cursor.execute("select username, password, role from user")
                        rows = self.cursor.fetchall()
                        um_list = []
                        for row in rows:
                            temp = {}
                            temp["username"] = row[0]
                            temp["password"] = row[1]
                            temp["role"] = row[2]
                            um_list.append(temp)
                        data = m_data(um_list)
                        err = request.args.get("err")
                        if err:
                            return render_template("UserManagement.html", data = data, msg = self.make_msg(err))
                        else:
                            return render_template("UserManagement.html", data = data)
                    else:
                        #修改密码
                        username = request.form.get("username")
                        password = request.form.get("password")
                        repeat = request.form.get("repeat")
                        if username and password and repeat:
                            #教工号不可为空
                            if self.input_valid(username) and self.input_valid(password) and self.input_valid(repeat):
                                #输入合法
                                self.cursor.execute("select username from user where username = '" + username + "'")
                                usn1 = self.cursor.fetchone()
                                if not usn1:
                                    return redirect("/?action=um&err=13")
                                if password != repeat:
                                    return redirect("/?action=um&err=14")
                                try:
                                    self.cursor.execute("update user set password = '" + password + "' where username = '" + username + "'")
                                    self.db.commit()
                                except:
                                    self.db.rollback()
                                return redirect("/?action=um")
                            else:
                                return redirect("/?action=um&err=2")
                        else:
                            return redirect("/?action=um&err=3")
                else:
                    return redirect("/?action=sm")
            elif role == 'teacher':
                tno = session.get('user')
                if request.method == "GET":
                        self.cursor.execute("select Sno, Sname, Sgender, Term from student join teacher on student.Sclass = teacher.Tclass and Tno = '" + tno + "'")
                        rows = self.cursor.fetchall()
                        m_list = []
                        row_num = 0
                        for row in rows:
                            temp = {}
                            temp["sno"] = row[0]
                            temp["name"] = row[1]
                            temp["gender"] = row[2]
                            temp["term"] = row[3]
                            self.cursor.execute("select Pro_Record, Pro_Score from sp where Sno = '" + temp['sno'] + "' order by Pno")
                            rows1 = self.cursor.fetchall()
                            if rows1[0][0]:
                                temp["50m_r"] = rows1[0][0]
                            else:
                                temp["50m_r"] = ""
                            if rows1[0][1]:
                                temp["50m_s"] = rows1[0][1]
                            else:
                                temp["50m_s"] = "无"
                            if rows1[1][0]:
                                temp["push_r"] = rows1[1][0]
                            else:
                                temp["push_r"] = ""
                            if rows1[1][1]:
                                temp["push_s"] = rows1[1][1]
                            else:
                                temp["push_s"] = "无"
                            if rows1[2][0]:
                                temp["jump_r"] = rows1[2][0]
                            else:
                                temp["jump_r"] = ""
                            if rows1[2][1]:
                                temp["jump_s"] = rows1[2][1]
                            else:
                                temp["jump_s"] = "无"
                            if rows1[3][0]:
                                temp["rise_r"] = rows1[3][0]
                            else:
                                temp["rise_r"] = ""
                            if rows1[3][1]:
                                temp["rise_s"] = rows1[3][1]
                            else:
                                temp["rise_s"] = "无"
                            if rows1[4][0]:
                                temp["up_r"] = rows1[4][0]
                            else:
                                temp["up_r"] = ""
                            if rows1[4][1]:
                                temp["up_s"] = rows1[4][1]
                            else:
                                temp["up_s"] = "无"
                            if rows1[5][0]:
                                temp["1000/800m_r"] = rows1[5][0].replace('.', '\'')
                            else:
                                temp["1000/800m_r"] = ""
                            if rows1[5][1]:
                                temp["1000/800m_s"] = rows1[5][1]
                            else:
                                temp["1000/800m_s"] = "无"
                            if rows1[6][0]:
                                temp["rope_r"] = rows1[6][0]
                            else:
                                temp["rope_r"] = ""
                            if rows1[6][1]:
                                temp["rope_s"] = rows1[6][1]
                            else:
                                temp["rope_s"] = "无"
                            if rows1[7][0]:
                                temp["2400/2000m_r"] = rows1[7][0].replace('.', '\'')
                            else:
                                temp["2400/2000m_r"] = ""
                            if rows1[7][1]:
                                temp["2400/2000m_s"] = rows1[7][1]
                            else:
                                temp["2400/2000m_s"] = "无"
                            if rows1[8][1]:
                                temp["app"] = rows1[8][1]
                            else:
                                temp["app"] = ""
                            if rows1[9][1]:
                                temp["write"] = rows1[9][1]
                            else:
                                temp["write"] = ""
                            if rows1[10][1]:
                                temp["sign"] = rows1[10][1]
                            else:
                                temp["sign"] = ""
                            if rows1[11][1]:
                                temp["special"] = rows1[11][1]
                            else:
                                temp["special"] = ""
                            self.cursor.execute("select Sgrade from student where Sno = '" + temp['sno'] + "'")
                            rows1 = self.cursor.fetchone()
                            if rows1[0]:
                                temp["total"] = rows1[0]
                            else:
                                temp["total"] = "无"
                            temp["rn"] = row_num
                            row_num += 1
                            m_list.append(temp)
                        data = m_data(m_list)
                        err = request.args.get("err")
                        if err:
                            return render_template("Teacher.html", data = data, msg = self.make_msg(err))
                        else:
                            return render_template("Teacher.html", data = data)
                else:
                    self.cursor.execute("select count(*) from student join teacher on student.Sclass = teacher.Tclass and Tno = '" + tno + "'")
                    row_sum = self.cursor.fetchone()[0]
                    for i in range(row_sum):
                        if request.form.get(str(i) + '-sno'):
                            sno = request.form.get(str(i) + '-sno')
                            if not self.input_valid(sno):
                                return redirect("/?err=2")
                            self.cursor.execute("select Sno from student where Sno = '" + sno + "'")
                            sno1 = self.cursor.fetchone()
                            if not sno1:
                                return redirect("/?err=2")
                            self.cursor.execute("select Sgender from student where Sno = '" + sno + "'")
                            gender = self.cursor.fetchone()[0]
                            self.cursor.execute("select Term from student where Sno = '" + sno + "'")
                            term = self.cursor.fetchone()[0]
                            exi_num = 0
                            for k, v in self.project_no.items():
                                if request.form.get(str(i) + '-' + k):
                                    record = request.form.get(str(i) + '-' + k)
                                    record = record.replace('\'', '.')
                                    try:
                                        float(record)
                                    except:
                                        return redirect("/?err=2")
                                    if v == '009' or v == '010' or v == '011' or term != '大一上' and v == '012':
                                        try:
                                            self.cursor.execute("update sp set Pro_Score = '" + record + "' where Sno = '" + sno + "' and Pno = '" + v + "'")
                                            self.db.commit()
                                            exi_num += 1
                                        except:
                                            self.db.rollback()
                                    elif ((gender == '男' and v != '005') or (gender == '女' and v != '004')) and (term == '大一上' and v != '012' or term != '大一上'):
                                        score = self.super_cal(v, record, gender)
                                        try:
                                            self.cursor.execute("update sp set Pro_Record = '" + record + "', Pro_Score = '" + score + "' where Sno = '" + sno + "' and Pno = '" + v + "'")
                                            self.db.commit()
                                            exi_num += 1
                                            if term != '大一上' and v != '007' and v != '008':
                                                exi_num -= 1
                                        except:
                                            self.db.rollback()
                            if exi_num == 6 and term != '大一上' or exi_num == 10 and term == '大一上':
                                if term == '大一上':
                                    self.cursor.execute("select sum(Pro_Score * 0.1) from sp where Sno = '" + sno + "' and Pro_Score != 'NULL'")
                                    total = self.cursor.fetchone()[0]
                                    total = '%(p).1f' % {'p': total}
                                    try:
                                        self.cursor.execute("update student set Sgrade = '" + total + "' where Sno = '" + sno + "'")
                                        self.db.commit()
                                    except:
                                        self.db.rollback()
                                else:
                                    self.cursor.execute("select sum(Pro_Score * 0.1) from sp where Sno = '" + sno + "' and (Pno = '007' or Pno = '009' or Pno = '010' or Pno = '011')")
                                    part1 = self.cursor.fetchone()[0]
                                    self.cursor.execute("select (Pro_Score * 0.2) from sp where Sno = '" + sno + "' and Pno = '008'")
                                    part2 = self.cursor.fetchone()[0]
                                    self.cursor.execute("select (Pro_Score * 0.4) from sp where Sno = '" + sno + "' and Pno = '012'")
                                    part3 = self.cursor.fetchone()[0]
                                    total = part1 + part2 + part3
                                    total = '%(p).1f' % {'p': total}
                                    try:
                                        self.cursor.execute("update student set Sgrade = '" + total + "' where Sno = '" + sno + "'")
                                        self.db.commit()
                                    except:
                                        self.db.rollback()
                    return redirect("/")
        else:
            return redirect("/login")


    def __del__(self):
        self.cursor.close()
        self.db.close()


class logout_view(views.View):
    def dispatch_request(self):
        session.clear()
        return redirect('/login')


class output_view(views.View):
    def __init__(self):
        self.db = POOL.connection()
        self.cursor = self.db.cursor()

    def dispatch_request(self):
        if not session.get('user'):
            return redirect("/login")
        username = session.get('user')
        self.cursor.execute("select role from user where username = '" + username + "'")
        login_role = self.cursor.fetchone()
        if not login_role:
            return redirect("/login")
        role = login_role[0]
        if role != 'teacher':
            return redirect("/login")
        tno = username
        headers = (u"学号", u"姓名", u"性别", u"学期", u"50米", u"50米得分", u"体前屈", u"体前屈得分", u"立定跳远", u"立定跳远得分", u"引体向上", u"引体向上得分", u"仰卧起坐", u"仰卧起坐得分", u"1000米", u"1000米得分", u"800米", u"800米得分", u"跳绳", u"跳绳得分", u"2400米", u"2400米得分", u"2000米", u"2000米得分", u"运动世界校园得分", u"理论得分", u"考勤得分", u"专项得分", u"总评")
        data = tablib.Dataset(headers = headers)
        self.cursor.execute("select Sno, Sname, Sgender, Term from student join teacher on student.Sclass = teacher.Tclass and Tno = '" + tno + "'")
        rows = self.cursor.fetchall()
        row_num = 0
        for row in rows:
            temp = {}
            temp["sno"] = row[0]
            temp["name"] = row[1]
            temp["gender"] = row[2]
            temp["term"] = row[3]
            self.cursor.execute("select Pro_Record, Pro_Score from sp where Sno = '" + temp['sno'] + "' order by Pno")
            rows1 = self.cursor.fetchall()
            if rows1[0][0]:
                temp["50m_r"] = rows1[0][0]
            else:
                temp["50m_r"] = ""
            if rows1[0][1]:
                temp["50m_s"] = rows1[0][1]
            else:
                temp["50m_s"] = ""
            if rows1[1][0]:
                temp["push_r"] = rows1[1][0]
            else:
                temp["push_r"] = ""
            if rows1[1][1]:
                temp["push_s"] = rows1[1][1]
            else:
                temp["push_s"] = ""
            if rows1[2][0]:
                temp["jump_r"] = rows1[2][0]
            else:
                temp["jump_r"] = ""
            if rows1[2][1]:
                temp["jump_s"] = rows1[2][1]
            else:
                temp["jump_s"] = ""
            if rows1[3][0]:
                temp["rise_r"] = rows1[3][0]
            else:
                temp["rise_r"] = ""
            if rows1[3][1]:
                temp["rise_s"] = rows1[3][1]
            else:
                temp["rise_s"] = ""
            if rows1[4][0]:
                temp["up_r"] = rows1[4][0]
            else:
                temp["up_r"] = ""
            if rows1[4][1]:
                temp["up_s"] = rows1[4][1]
            else:
                temp["up_s"] = ""
            if rows1[5][0]:
                temp["1000/800m_r"] = rows1[5][0].replace('.', '\'')
            else:
                temp["1000/800m_r"] = ""
            if rows1[5][1]:
                temp["1000/800m_s"] = rows1[5][1]
            else:
                temp["1000/800m_s"] = ""
            if rows1[6][0]:
                temp["rope_r"] = rows1[6][0]
            else:
                temp["rope_r"] = ""
            if rows1[6][1]:
                temp["rope_s"] = rows1[6][1]
            else:
                temp["rope_s"] = ""
            if rows1[7][0]:
                temp["2400/2000m_r"] = rows1[7][0].replace('.', '\'')
            else:
                temp["2400/2000m_r"] = ""
            if rows1[7][1]:
                temp["2400/2000m_s"] = rows1[7][1]
            else:
                temp["2400/2000m_s"] = ""
            if rows1[8][1]:
                temp["app"] = rows1[8][1]
            else:
                temp["app"] = ""
            if rows1[9][1]:
                temp["write"] = rows1[9][1]
            else:
                temp["write"] = ""
            if rows1[10][1]:
                temp["sign"] = rows1[10][1]
            else:
                temp["sign"] = ""
            if rows1[11][1]:
                temp["special"] = rows1[11][1]
            else:
                temp["special"] = ""
            self.cursor.execute("select Sgrade from student where Sno = '" + temp['sno'] + "'")
            rows1 = self.cursor.fetchone()
            if rows1[0]:
                temp["total"] = rows1[0]
            else:
                temp["total"] = ""
            temp["rn"] = row_num
            row_num += 1
            if temp["gender"] == '男':
                row2 = [temp["sno"], temp["name"], temp["gender"], temp["term"], temp["50m_r"], temp["50m_s"], temp["push_r"], temp["push_s"], temp["jump_r"], temp["jump_s"], temp["rise_r"], temp["rise_s"], temp["up_r"], temp["up_s"], temp["1000/800m_r"], temp["1000/800m_s"], u"", u"", temp["rope_r"], temp["rope_s"], temp["2400/2000m_r"], temp["2400/2000m_s"], u"", u"", temp["app"], temp["write"], temp["sign"], temp["special"], temp["total"]]
            elif temp["gender"] == '女':
                row2 = [temp["sno"], temp["name"], temp["gender"], temp["term"], temp["50m_r"], temp["50m_s"], temp["push_r"], temp["push_s"], temp["jump_r"], temp["jump_s"], temp["rise_r"], temp["rise_s"], temp["up_r"], temp["up_s"], u"", u"", temp["1000/800m_r"], temp["1000/800m_s"], temp["rope_r"], temp["rope_s"], u"", u"", temp["2400/2000m_r"], temp["2400/2000m_s"], temp["app"], temp["write"], temp["sign"], temp["special"], temp["total"]]
            data.append(row2)
        open('grade-' + tno + '.xlsx', 'wb').write(data.xlsx)
        response = make_response(send_file("grade-" + tno + ".xlsx"))
        response.headers["Content-Disposition"] = "attachment; filename=grade-" + tno + ".xlsx;"
        return response

    def __del__(self):
        self.cursor.close()
        self.db.close()

app.add_url_rule('/', view_func=index_view.as_view('index'), methods=["GET", "POST"])
app.add_url_rule('/login', view_func=login_view.as_view('login'), methods=["GET", "POST"])
app.add_url_rule('/logout', view_func=logout_view.as_view('logout'), methods=["GET"])
app.add_url_rule('/output', view_func=output_view.as_view('output'), methods=["GET"])

if __name__ == '__main__':
    app.run(debug = True, port = '80')
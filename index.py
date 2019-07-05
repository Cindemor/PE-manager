from flask import render_template, Flask, views, request, redirect, session, send_from_directory
from DBUtils.PooledDB import PooledDB
import pymysql

app = Flask(__name__)
app.secret_key = "secret_key"

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
                    return 'not permitted'
            else:
                return 'not permitted'
        else:
            if session.get('user'):
                #已登录
                return redirect("/")
            else:
                return render_template("login.html")

    def __del__(self):
        self.cursor.close()
        self.db.close()


class index_view(views.View):
    def __init__(self):
        self.db = POOL.connection()
        self.cursor = self.db.cursor()

    def input_valid(self, words):
        if "'" in words:
            return False
        return True

    def show_record(self, pno, record, unit):
        res = ""
        if pno == "002":
            res = str(int(record) // 60) + "分" + str(int(record) % 60) + "秒"
        else:
            res = record + unit
        return res

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
                    temp = {}
                    temp["pname"] = row[3]
                    temp["grade"] = row[2]
                    pno = row[4]
                    unit = row[1]
                    record = row[0]
                    record = self.show_record(pno, record, unit)
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
                                        return "此学号已存在"
                                    if not cno:
                                        return "课程号不存在"
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
                                    return redirect("/?action=sm")
                                else:
                                    return "非法输入"
                            else:
                                return "任意一项内容均不能为空"
                        elif mode == "delete":
                            #删除学生
                            if sno:
                                #学号不可为空
                                if self.input_valid(sno):
                                    #输入合法
                                    self.cursor.execute("select Sno from student where Sno = '" + sno + "'")
                                    sno1 = self.cursor.fetchone()
                                    if not sno1:
                                        return "此学号不存在"
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
                                    return "非法输入"
                            else:
                                return "学号不能为空"
                        elif mode == "update":
                            #更新学生信息
                            if sno:
                                #学号不可为空
                                if self.input_valid(sno) and self.input_valid(term) and self.input_valid(classno):
                                    #输入合法
                                    self.cursor.execute("select Sno from student where Sno = '" + sno + "'")
                                    sno1 = self.cursor.fetchone()
                                    if not sno1:
                                        return "此学号不存在"
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
                                            return "课程号不存在"
                                        try:
                                            self.cursor.execute("update student set Sclass = '" + classno + "' where Sno = '" + sno + "'")
                                            self.db.commit()
                                        except:
                                            self.db.rollback()
                                    return redirect("/?action=sm")
                                else:
                                    return "非法输入"
                            else:
                                return "学号不能为空"
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
                                return "非法输入"
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
                                        return "此教工号已存在"
                                    if not cno1:
                                        return "课程号不存在"
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
                                    return "非法输入"
                            else:
                                return "任意一项内容均不能为空"
                        elif mode == "delete":
                            #删除教师
                            if tno:
                                #教工号不可为空
                                if self.input_valid(tno):
                                    #输入合法
                                    self.cursor.execute("select Tno from teacher where Tno = '" + tno + "'")
                                    tno1 = self.cursor.fetchone()
                                    if not tno1:
                                        return "此教工号不存在"
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
                                    return "非法输入"
                            else:
                                return "教工号不能为空"
                        elif mode == "update":
                            #更新教师信息
                            if tno:
                                #教工号不可为空
                                if self.input_valid(tno) and self.input_valid(classno):
                                    #输入合法
                                    self.cursor.execute("select Tno from teacher where Tno = '" + tno + "'")
                                    tno1 = self.cursor.fetchone()
                                    if not tno1:
                                        return "此教工号不存在"
                                    if classno:
                                        self.cursor.execute("select Cno from course where Cno = '" + classno + "'")
                                        cno = self.cursor.fetchone()
                                        if not cno:
                                            return "课程号不存在"
                                        try:
                                            self.cursor.execute("update teacher set Tclass = '" + classno + "' where Tno = '" + tno + "'")
                                            self.db.commit()
                                        except:
                                            self.db.rollback()
                                    return redirect("/?action=tm")
                                else:
                                    return "非法输入"
                            else:
                                return "教工号不能为空"
                        elif mode == "search":
                            #查询教师信息
                            sql = "select Tno, Tname, Tgender, Tclass, Cname from teacher left join course on teacher.Tclass = course.cno"
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
                                return "非法输入"
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
                                        return "此课程号已存在"
                                    try:
                                        self.cursor.execute("insert into course values('" + cno + "', '" + cname + "')")
                                        self.db.commit()
                                    except:
                                        self.db.rollback()
                                    return redirect("/?action=cm")
                                else:
                                    return "非法输入"
                            else:
                                return "任意一项内容均不能为空"
                        elif mode == "delete":
                            #删除课程
                            if cno:
                                #课程号不可为空
                                if self.input_valid(cno):
                                    #输入合法
                                    self.cursor.execute("select Cno from course where Cno = '" + cno + "'")
                                    cno1 = self.cursor.fetchone()
                                    if not cno1:
                                        return "此课程号不存在"
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
                                    return "非法输入"
                            else:
                                return "课程号不能为空"
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
                                return "非法输入"
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
                                    return "此用户不存在"
                                if password != repeat:
                                    return "两次输入密码不一致"
                                try:
                                    self.cursor.execute("update user set password = '" + password + "' where username = '" + username + "'")
                                    self.db.commit()
                                except:
                                    self.db.rollback()
                                return redirect("/?action=um")
                            else:
                                return "非法输入"
                        else:
                            return "任意一项内容均不能为空"
                else:
                    return redirect("/?action=sm")
            elif role == 'teacher':
                return render_template("Teacher.html")
        else:
            return 'not permitted'


    def __del__(self):
        self.cursor.close()
        self.db.close()


class logout_view(views.View):
    def __init__(self):
        self.db = POOL.connection()
        self.cursor = self.db.cursor()

    def dispatch_request(self):
        session.clear()
        return redirect('/login')

    def __del__(self):
        self.cursor.close()
        self.db.close()


app.add_url_rule('/', view_func=index_view.as_view('index'), methods=["GET", "POST"])
app.add_url_rule('/login', view_func=login_view.as_view('login'), methods=["GET", "POST"])
app.add_url_rule('/logout', view_func=logout_view.as_view('logout'), methods=["GET"])

if __name__ == '__main__':
    app.run(debug = True, port = '80')
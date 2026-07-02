import mysql.connector
from mysql.connector import pooling
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os, random, string, base64, json, time, uuid

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# 数据库连接池 - 扩大连接数避免pool exhausted
db_config = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "xuexin"),
    "pool_name": "mypool",
    "pool_size": 20,
}
pool = None

def get_db():
    global pool
    if pool is None:
        pool = mysql.connector.pooling.MySQLConnectionPool(**db_config)
    return pool.get_connection()

def init_db():
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(50) NOT NULL,
                gender VARCHAR(4) NOT NULL,
                id_card VARCHAR(20) NOT NULL,
                photo LONGTEXT,
                photo_old LONGTEXT,
                birth VARCHAR(20),
                ethnic VARCHAR(20) DEFAULT '汉族',
                school VARCHAR(100),
                level VARCHAR(20) DEFAULT '本科',
                duration VARCHAR(10) DEFAULT '4年',
                major VARCHAR(100),
                degree_type VARCHAR(50) DEFAULT '普通高等教育',
                study_form VARCHAR(50) DEFAULT '普通全日制',
                college VARCHAR(100),
                dept VARCHAR(100),
                enroll_date VARCHAR(20),
                grad_date VARCHAR(20),
                status VARCHAR(30) DEFAULT '在籍',
                verify_code VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # 兼容已存在的表：加 photo_old 列
        try:
            cursor.execute("ALTER TABLE accounts ADD COLUMN photo_old LONGTEXT")
        except:
            pass
        # 去掉UNIQUE约束、添加索引加速查询
        try:
            cursor.execute("ALTER TABLE accounts DROP INDEX id_card")
        except:
            pass
        try:
            cursor.execute("CREATE INDEX idx_id_card ON accounts(id_card)")
            cursor.execute("CREATE INDEX idx_name ON accounts(name)")
        except:
            pass
        conn.commit()
    finally:
        cursor.close()
        conn.close()

@app.on_event("startup")
def startup():
    for i in range(30):
        try:
            init_db()
            print("✅ 数据库初始化成功")
            return
        except Exception as e:
            print(f"⏳ 等待数据库就绪 ({i+1}/30)...")
            import time
            time.sleep(2)
    print("❌ 数据库连接失败")

# ---------- 数据模型 ----------
class RegisterRequest(BaseModel):
    name: str = ""
    gender: str
    photo: str = ""
    photo_old: str = ""
    id_card: str = ""

class UpdateRequest(BaseModel):
    name: str = ""
    gender: str = ""
    id_card: str = ""
    photo: str = ""
    photo_old: str = ""

class LoginRequest(BaseModel):
    name: str
    id_card: str

# ---------- 工具函数 ----------
def random_pick(arr):
    return arr[random.choice(list(range(len(arr))))]

def generate_random_code(length=16):
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    return ''.join(random.choice(chars) for _ in range(length))

def calc_id_check_digit(first17: str) -> str:
    """计算身份证第18位校验码（ISO 7064:1983 MOD 11-2）"""
    weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
    check_map = ['1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2']
    total = sum(int(first17[i]) * weights[i] for i in range(17))
    return check_map[total % 11]

def generate_full_account(name, gender, photo="", id_card="", photo_old=""):
    schools = [
        '运城学院','太原师范学院','忻州师范学院','山西师范大学','山西财经大学','山西医科大学','山西农业大学','中北大学','太原科技大学','山西大同大学','长治学院','晋中学院',
        '洛阳师范学院','信阳师范学院','安阳师范学院','南阳师范学院','商丘师范学院','许昌学院','河南科技大学','河南理工大学','河南工业大学','河南财经政法大学','郑州轻工业大学','中原工学院','周口师范学院','黄淮学院','平顶山学院','新乡学院',
        '滁州学院','皖西学院','宿州学院','巢湖学院','黄山学院','铜陵学院','合肥学院','安徽科技学院','安徽理工大学','安徽工业大学','安徽建筑大学','蚌埠学院','池州学院','亳州学院',
        '莆田学院','三明学院','龙岩学院','武夷学院','闽江学院','厦门理工学院','泉州师范学院','福建江夏学院','宁德师范学院','福建技术师范学院',
        '九江学院','宜春学院','上饶师范学院','景德镇学院','萍乡学院','新余学院','赣南师范大学','江西科技师范大学','南昌工程学院','井冈山大学',
        '德州学院','滨州学院','泰山学院','枣庄学院','菏泽学院','潍坊学院','济宁学院','山东青年政治学院','山东管理学院','山东农业工程学院',
        '湖北工程学院','湖北科技学院','湖北文理学院','湖北汽车工业学院','湖北理工学院','荆楚理工学院','汉江师范学院','黄冈师范学院','武汉商学院',
        '湖南科技学院','湖南人文科技学院','湖南工学院','湖南城市学院','邵阳学院','怀化学院','湘南学院','长沙师范学院','湖南女子学院',
        '韶关学院','惠州学院','东莞理工学院','五邑大学','肇庆学院','茂名学院','嘉应学院','广州航海学院','广东石油化工学院',
        '广西科技大学','桂林理工大学','桂林电子科技大学','北部湾大学','河池学院','玉林师范学院','百色学院','贺州学院','梧州学院',
        '绵阳师范学院','内江师范学院','宜宾学院','西昌学院','攀枝花学院','成都工业学院','四川旅游学院','成都大学',
        '贵州师范大学','贵州财经大学','贵州医科大学','遵义医科大学','贵州理工学院','六盘水师范学院','安顺学院','凯里学院',
        '宝鸡文理学院','咸阳师范学院','渭南师范学院','安康学院','商洛学院','榆林学院','西安航空学院','陕西学前师范学院',
        '天水师范学院','河西学院','陇东学院','甘肃民族师范学院','兰州城市学院','兰州文理学院','甘肃医学院',
        '黑龙江科技大学','佳木斯大学','齐齐哈尔大学','牡丹江师范学院','大庆师范学院','黑河学院','绥化学院',
        '北华大学','吉林师范大学','长春师范大学','通化师范学院','白城师范学院','吉林化工学院','吉林农业科技学院',
        '辽宁科技大学','辽宁工业大学','沈阳化工大学','大连交通大学','渤海大学','鞍山师范学院','辽东学院','沈阳工程学院',
        '曲靖师范学院','玉溪师范学院','楚雄师范学院','红河学院','文山学院','普洱学院','保山学院','昭通学院',
        '淮阴师范学院','盐城师范学院','江苏理工学院','常州工学院','徐州工程学院','泰州学院','南京晓庄学院','江苏海洋大学',
        '绍兴文理学院','嘉兴学院','台州学院','丽水学院','衢州学院','浙江水利水电学院','浙江外国语学院','宁波工程学院',
        '河北科技大学','河北建筑工程学院','河北北方学院','河北科技师范学院','唐山学院','廊坊师范学院','邢台学院','衡水学院',
        '内蒙古科技大学','内蒙古工业大学','内蒙古民族大学','赤峰学院','呼伦贝尔学院','河套学院',
    ]
    majors = ['计算机科学与技术','软件工程','信息与计算科学','数学与应用数学','物理学','化学','生物科学','汉语言文学','英语','历史学','思想政治教育','学前教育','小学教育','体育教育','社会体育指导与管理','音乐学','美术学','视觉传达设计','环境设计','产品设计','服装与服饰设计','数字媒体技术','网络工程','物联网工程','数据科学与大数据技术','人工智能','机器人工程','自动化','电气工程及其自动化','电子信息工程','通信工程','光电信息科学与工程','微电子科学与工程','机械设计制造及其自动化','材料成型及控制工程','工业设计','车辆工程','汽车服务工程','土木工程','建筑环境与能源应用工程','给排水科学与工程','建筑学','城乡规划','风景园林','工程管理','工程造价','工商管理','市场营销','会计学','财务管理','人力资源管理','旅游管理','酒店管理','电子商务','物流管理','物流工程','国际经济与贸易','金融学','经济学','经济统计学','财政学','税收学','保险学','法学','社会工作','公共事业管理','行政管理','劳动与社会保障','土地资源管理','地理科学','自然地理与资源环境','人文地理与城乡规划','应用心理学','教育技术学','食品科学与工程','食品质量与安全','生物工程','制药工程','化学工程与工艺','应用化学','环境工程','环境科学','材料科学与工程','材料化学','高分子材料与工程','新能源科学与工程','新能源材料与器件','测绘工程','地质工程','矿物加工工程','安全工程','护理学','药学','中药学','医学检验技术','医学影像技术','康复治疗学','口腔医学技术','眼视光学','信息管理与信息系统','工业工程','标准化工程','质量管理工程','采购管理','审计学','资产评估']
    gender_char = gender if gender else random_pick(['男','女'])
    # 姓名如果为空则自动生成（根据性别区分）
    if not name:
        first = random_pick(['赵','钱','孙','李','周','吴','郑','王','冯','陈','褚','卫','蒋','沈','韩','杨','朱','秦','尤','许','何','吕','施','张','孔','曹','严','华','金','魏','陶','姜','戚','谢','邹','喻','柏','水','窦','章','云','苏','潘','葛','奚','范','彭','郎','鲁','韦','昌','马','苗','凤','花','方','俞','任','袁','柳','酆','鲍','史','唐','费','廉','岑','薛','雷','贺','倪','汤','滕','殷','罗','毕','郝','邬','安','常','乐','于','时','傅','皮','卞','齐','康','伍','余','元','卜','顾','孟','平','黄','萧','程'])
        if gender_char == '女':
            last1 = random_pick(['婷','芳','丽','敏','静','玲','雪','娟','丹','娜','怡','慧','琳','洁','瑶','欣','雨','涵','萱','思','颖','嘉','莹','秀','文','雅','清','燕','莉','萍','美','蓉','春','怡','佳','蕊','月','蝶','灵','菲','蝶'])
            last2 = random_pick(['萍','芬','芳','燕','红','英','兰','琴','玲','霞','琳','敏','婷','欣','涵','宁','雪','瑶','萱','蕊','娜','倩','薇','柔'])
        else:
            last1 = random_pick(['明','华','超','军','勇','伟','强','磊','文','杰','涛','斌','鑫','浩','鹏','飞','宇','峰','俊','辉','建','志','海','宏','成','亮','旭','刚','平','辉','龙','元','天'])
            last2 = random_pick(['伟','勇','军','杰','强','斌','明','华','超','磊','涛','鹏','飞','宇','峰','俊','辉'])
        name = first + last1 + (last2 if random.random() < 0.6 else '')
    # 学籍信息
    school = random_pick(schools)
    level = '本科'
    major = random_pick(majors)
    degree_type = '普通高等教育'
    study_form = '普通全日制'
    duration = '4 年'
    # 毕业年份从2027年7月1日起，入学年份2023-2026，毕业2027-2030
    enroll_year = random.randint(2023, 2026)
    enroll_month = '09'
    enroll_day = '01'
    grad_year = enroll_year + int(duration.split(' ')[0])
    enroll_date = f'{enroll_year}年{enroll_month}月{enroll_day}日'
    grad_date = f'{grad_year}年07月01日'
    status = '在籍（注册学籍）'
    # 用户是否提供了身份证号
    if id_card and len(id_card.strip()) >= 14:
        # 从用户提供的身份证号提取出生日期和性别
        cid = id_card.strip().replace(' ', '').replace('-', '')
        birth_year = int(cid[6:10])
        birth_month = int(cid[10:12])
        birth_day = int(cid[12:14])
        birth = f'{birth_year}年{birth_month:02d}月{birth_day:02d}日'
        # 从身份证第17位推断性别
        gender_digit = int(cid[16]) if len(cid) >= 17 else 0
        gender_char = '男' if gender_digit % 2 == 1 else '女'
    else:
        # 自动生成合理的出生日期（入学时18-20岁）
        birth_year = enroll_year - random.randint(18, 20)
        birth_month = random.randint(1, 12)
        birth_day = random.randint(1, 28)
        birth = f'{birth_year}年{birth_month:02d}月{birth_day:02d}日'
        # 根据出生日期和性别生成身份证号（符合GB 11643-1999标准）
        area_code = '14' + str(random.randint(1000, 9999)).zfill(4)
        birth_part = f'{birth_year}{birth_month:02d}{birth_day:02d}'
        seq_prefix = random.randint(10, 99)
        if gender_char == '男':
            gd = random_pick(['1','3','5','7','9'])
        else:
            gd = random_pick(['0','2','4','6','8'])
        first17 = area_code + birth_part + str(seq_prefix) + gd
        check_digit = calc_id_check_digit(first17)
        id_card = first17 + check_digit
    ethnic = random_pick(['汉族','汉族','汉族','汉族','汉族','汉族','汉族','汉族','汉族','蒙古族','回族','藏族','苗族','彝族','壮族'])

    return {
        "name": name,
        "gender": gender_char,
        "id_card": id_card,
        "photo": photo,
        "photo_old": photo_old,
        "birth": birth,
        "ethnic": ethnic,
        "school": school,
        "level": level,
        "duration": duration,
        "major": major,
        "degree_type": degree_type,
        "study_form": study_form,
        "college": school,
        "dept": major.split('(')[0] + '系' if '(' in major else major + '系',
        "enroll_date": enroll_date,
        "grad_date": grad_date,
        "status": status,
        "verify_code": generate_random_code(),
    }

# ---------- 扫码登录（内存 Token） ----------
scan_tokens = {}

def _cleanup_expired():
    now = time.time()
    for t in list(scan_tokens.keys()):
        if now - scan_tokens[t]["created_at"] > 300:
            del scan_tokens[t]

@app.post("/api/scan-login/create")
def create_scan_token():
    """生成一次性扫码登录 token"""
    _cleanup_expired()
    token = uuid.uuid4().hex
    scan_tokens[token] = {"status": "pending", "user_id": None, "created_at": time.time()}
    return {"code": 0, "token": token}

@app.get("/api/scan-login/status/{token}")
def check_scan_status(token: str):
    """轮询扫码状态"""
    data = scan_tokens.get(token)
    if not data or time.time() - data["created_at"] > 300:
        scan_tokens.pop(token, None)
        return {"code": -1, "status": "expired", "message": "二维码已过期"}
    if data["status"] == "confirmed" and data["user_id"]:
        conn = get_db()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM accounts WHERE id=%s", (data["user_id"],))
            user = cursor.fetchone()
            if user:
                user["photo"] = user["photo"] or ""
                return {"code": 0, "status": "confirmed", "user": user}
        finally:
            cursor.close()
            conn.close()
    return {"code": 0, "status": data["status"]}

@app.post("/api/scan-login/confirm/{token}")
def confirm_scan_login(token: str, user_id: int = 0):
    """手机端确认登录"""
    data = scan_tokens.get(token)
    if not data or time.time() - data["created_at"] > 300:
        scan_tokens.pop(token, None)
        raise HTTPException(status_code=404, detail="二维码已过期")
    if not user_id:
        raise HTTPException(status_code=400, detail="请提供用户ID")
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM accounts WHERE id=%s", (user_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="用户不存在")
    finally:
        cursor.close()
        conn.close()
    data["status"] = "confirmed"
    data["user_id"] = user_id
    return {"code": 0, "message": "确认登录成功"}

# ---------- 路由 ----------
@app.post("/api/register")
def register(req: RegisterRequest):
    info = generate_full_account(req.name, req.gender, req.photo, req.id_card, req.photo_old)
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO accounts (name, gender, id_card, photo, photo_old, birth, ethnic, school, level, duration,
            major, degree_type, study_form, college, dept, enroll_date, grad_date, status, verify_code)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            info["name"], info["gender"], info["id_card"], info["photo"], info["photo_old"],
            info["birth"], info["ethnic"], info["school"], info["level"], info["duration"],
            info["major"], info["degree_type"], info["study_form"], info["college"],
            info["dept"], info["enroll_date"], info["grad_date"], info["status"], info["verify_code"]
        ))
        conn.commit()
        user_id = cursor.lastrowid
        info["id"] = user_id
        return {"code": 0, "message": "注册成功", "data": info}
    finally:
        cursor.close()
        conn.close()

@app.post("/api/login")
def login(req: LoginRequest):
    conn = get_db()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM accounts WHERE name=%s AND id_card=%s", (req.name, req.id_card))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="姓名或身份证号错误")
        user["photo"] = user["photo"] or ""
        return {"code": 0, "message": "登录成功", "data": user}
    finally:
        cursor.close()
        conn.close()

@app.get("/api/user/{user_id}")
def get_user(user_id: int):
    conn = get_db()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM accounts WHERE id=%s", (user_id,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        user["photo"] = user["photo"] or ""
        user["photo_old"] = user.get("photo_old") or ""
        return {"code": 0, "data": user}
    finally:
        cursor.close()
        conn.close()

@app.put("/api/user/{user_id}")
def update_user(user_id: int, req: UpdateRequest):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM accounts WHERE id=%s", (user_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="用户不存在")

        # 动态构建 SQL：只更新提供的字段
        fields = []
        values = []
        if req.name:
            fields.append("name=%s")
            values.append(req.name)
        if req.gender:
            fields.append("gender=%s")
            values.append(req.gender)
        if req.id_card:
            fields.append("id_card=%s")
            values.append(req.id_card)
        # photo 允许设为空字符串以清除
        if req.photo is not None and req.photo != "":
            fields.append("photo=%s")
            values.append(req.photo)
        if req.photo_old is not None and req.photo_old != "":
            fields.append("photo_old=%s")
            values.append(req.photo_old)

        if not fields:
            return {"code": 0, "message": "无更新"}

        values.append(user_id)
        sql = "UPDATE accounts SET " + ", ".join(fields) + " WHERE id=%s"
        cursor.execute(sql, values)
        conn.commit()
        return {"code": 0, "message": "更新成功"}
    finally:
        cursor.close()
        conn.close()

@app.get("/api/users")
def list_users():
    conn = get_db()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, name, gender, id_card, birth, ethnic, school, level, duration, major, degree_type, study_form, college, dept, enroll_date, grad_date, status, verify_code, created_at FROM accounts ORDER BY created_at DESC")
        return {"code": 0, "data": cursor.fetchall()}
    finally:
        cursor.close()
        conn.close()

@app.delete("/api/user/{user_id}")
def delete_user(user_id: int):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM accounts WHERE id=%s", (user_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="用户不存在")
        cursor.execute("DELETE FROM accounts WHERE id=%s", (user_id,))
        conn.commit()
        return {"code": 0, "message": "删除成功"}
    finally:
        cursor.close()
        conn.close()

@app.delete("/api/users/batch-delete")
def batch_delete_recent(count: int = 100):
    """删除最老 N 条账号 (按 created_at 正序)"""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM accounts ORDER BY created_at ASC LIMIT %s", (count,))
        ids = [row[0] for row in cursor.fetchall()]
        if not ids:
            return {"code": 0, "message": "没有可删除的账号", "deleted": 0}
        placeholders = ','.join(['%s'] * len(ids))
        cursor.execute(f"DELETE FROM accounts WHERE id IN ({placeholders})", ids)
        conn.commit()
        return {"code": 0, "message": f"成功删除 {len(ids)} 条", "deleted": len(ids)}
    finally:
        cursor.close()
        conn.close()

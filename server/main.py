import mysql.connector
from mysql.connector import pooling
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os, random, string, base64, json

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# 数据库连接池
db_config = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "xuexin"),
    "pool_name": "mypool",
    "pool_size": 5,
}
pool = None

def get_db():
    global pool
    if pool is None:
        pool = mysql.connector.pooling.MySQLConnectionPool(**db_config)
    return pool.get_connection()

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(50) NOT NULL,
            gender VARCHAR(4) NOT NULL,
            id_card VARCHAR(20) NOT NULL UNIQUE,
            photo LONGTEXT,
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

    # 添加索引加速查询
    try:
        cursor.execute("CREATE INDEX idx_id_card ON accounts(id_card)")
        cursor.execute("CREATE INDEX idx_name ON accounts(name)")
    except:
        pass  # 索引已存在忽略
    conn.commit()
    cursor.close()
    conn.close()

@app.on_event("startup")
def startup():
    # 重试连接数据库
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

class LoginRequest(BaseModel):
    name: str
    id_card: str

# ---------- 工具函数 ----------
def random_pick(arr):
    return arr[random.choice(list(range(len(arr))))]

def generate_random_code(length=16):
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    return ''.join(random.choice(chars) for _ in range(length))

def generate_full_account(name, gender, photo=""):
    # 学校/专业池
    schools = ['运城学院','太原师范学院','忻州师范学院','山西师范大学','山西财经大学','山西医科大学','山西农业大学','中北大学',
               '洛阳师范学院','信阳师范学院','安阳师范学院','南阳师范学院','商丘师范学院','许昌学院','滁州学院','皖西学院',
               '宿州学院','巢湖学院','黄山学院','铜陵学院','合肥学院','莆田学院','三明学院','龙岩学院','武夷学院']
    majors = ['计算机科学与技术(网络工程方向)','计算机科学与技术','软件工程','网络工程','物联网工程','数据科学与大数据技术',
              '电子信息工程','通信工程','自动化','电气工程及其自动化','汉语言文学','英语','日语','商务英语',
              '数学与应用数学','金融学','经济学','会计学','财务管理','市场营销','法学','学前教育','小学教育']
    depts = ['计算机科学与技术系','软件工程系','电子信息工程系','自动化系','网络工程系','经济管理学院','法学院','外国语学院',
             '人文学院','理学院','教育学院','美术与设计学院']
    ethnics = ['汉族']

    # 生成身份证
    now = 2026
    age = random.randint(20, 22)
    birth_year = now - age
    birth_month = str(random.randint(1, 12)).zfill(2)
    birth_day = str(random.randint(1, 28)).zfill(2)
    birth = f"{birth_year}年{birth_month}月{birth_day}日"
    nums = f"{birth_year}{birth_month}{birth_day}"
    area = random_pick(['110101','110102','310101','310104','440101','440301','330101','320101','210101','420101'])
    # 前2位顺序码随机 + 第3位奇男偶女
    seq_first = str(random.randint(0, 99)).zfill(2)
    gcode = random_pick(['1','3','5','7','9']) if gender == '男' else random_pick(['0','2','4','6','8'])
    seq = seq_first + gcode  # 3位顺序码，末位标记性别
    full17 = area + nums + seq  # 6+8+3=17位
    ws = [7,9,10,5,8,4,2,1,6,3,7,9,10,5,8,4,2]
    cs = ['1','0','X','9','8','7','6','5','4','3','2']
    s = sum(int(full17[i]) * ws[i] for i in range(17))
    id_card = full17 + cs[s % 11]

    enroll_year = birth_year + 18
    grad_year = enroll_year + 4
    school = random_pick(schools)

    return {
        "name": name,
        "gender": gender,
        "id_card": id_card,
        "photo": photo,
        "birth": birth,
        "ethnic": random_pick(ethnics),
        "school": school,
        "level": "本科",
        "duration": "4年",
        "major": random_pick(majors),
        "degree_type": "普通高等教育",
        "study_form": "普通全日制",
        "college": school,
        "dept": random_pick(depts),
        "enroll_date": f"{enroll_year}年09月01日",
        "grad_date": f"{grad_year}年07月01日",
        "status": "在籍",
        "verify_code": generate_random_code(16),
    }

# ---------- API ----------
@app.post("/api/register")
def register(req: RegisterRequest):
    # 如果姓名为空，自动生成
    name = req.name.strip() if req.name and req.name.strip() else ""
    if not name:
        names_male = ['张晓斌','王磊','张伟','刘洋','杨帆','周杰','吴迪','徐明','马超','胡波','郭峰','林峰','何平','高峰','陈浩','赵磊','孙权','李强','黄海','刘杰']
        names_female = ['李娜','陈静','赵敏','黄丽','孙悦','朱婷','王芳','张娟','刘洋','杨雪','周婷','吴静','马丽','胡敏','郭雪','林婷','何悦','高敏','陈静怡','赵梦']
        name_list = names_male if req.gender == '男' else names_female
        name = random.choice(name_list)
    info = generate_full_account(name, req.gender, req.photo)
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO accounts (name, gender, id_card, photo, birth, ethnic, school, level, duration,
            major, degree_type, study_form, college, dept, enroll_date, grad_date, status, verify_code)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            info["name"], info["gender"], info["id_card"], info["photo"],
            info["birth"], info["ethnic"], info["school"], info["level"], info["duration"],
            info["major"], info["degree_type"], info["study_form"], info["college"],
            info["dept"], info["enroll_date"], info["grad_date"], info["status"], info["verify_code"]
        ))
        conn.commit()
        user_id = cursor.lastrowid
        info["id"] = user_id
        return {"code": 0, "message": "注册成功", "data": info}
    except mysql.connector.IntegrityError:
        raise HTTPException(status_code=400, detail="身份证号已存在")
    finally:
        cursor.close()
        conn.close()

@app.post("/api/login")
def login(req: LoginRequest):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM accounts WHERE name=%s AND id_card=%s", (req.name, req.id_card))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    if not user:
        raise HTTPException(status_code=404, detail="姓名或身份证号错误")
    user["photo"] = user["photo"] or ""
    return {"code": 0, "message": "登录成功", "data": user}

@app.get("/api/user/{user_id}")
def get_user(user_id: int):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM accounts WHERE id=%s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    user["photo"] = user["photo"] or ""
    return {"code": 0, "data": user}

@app.get("/api/users")
def list_users():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, name, gender, id_card, birth, ethnic, school, level, duration, major, degree_type, study_form, college, dept, enroll_date, grad_date, status, verify_code, created_at FROM accounts ORDER BY created_at DESC")
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return {"code": 0, "data": users}

@app.delete("/api/user/{user_id}")
def delete_user(user_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM accounts WHERE id=%s", (user_id,))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="用户不存在")
    cursor.execute("DELETE FROM accounts WHERE id=%s", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return {"code": 0, "message": "删除成功"}

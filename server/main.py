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
            id_card VARCHAR(20) NOT NULL,
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

    # 去掉UNIQUE约束、添加索引加速查询
    try:
        cursor.execute("ALTER TABLE accounts DROP INDEX id_card")
    except:
        pass
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
    id_card: str = ""

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
    schools = [
        # 山西
        '运城学院','太原师范学院','忻州师范学院','山西师范大学','山西财经大学','山西医科大学','山西农业大学','中北大学','太原科技大学','山西大同大学','长治学院','晋中学院',
        # 河南
        '洛阳师范学院','信阳师范学院','安阳师范学院','南阳师范学院','商丘师范学院','许昌学院','河南科技大学','河南理工大学','河南工业大学','河南财经政法大学','郑州轻工业大学','中原工学院','周口师范学院','黄淮学院','平顶山学院','新乡学院',
        # 安徽
        '滁州学院','皖西学院','宿州学院','巢湖学院','黄山学院','铜陵学院','合肥学院','安徽科技学院','安徽理工大学','安徽工业大学','安徽建筑大学','蚌埠学院','池州学院','亳州学院',
        # 福建
        '莆田学院','三明学院','龙岩学院','武夷学院','闽江学院','厦门理工学院','泉州师范学院','福建江夏学院','宁德师范学院','福建技术师范学院',
        # 江西
        '九江学院','宜春学院','上饶师范学院','景德镇学院','萍乡学院','新余学院','赣南师范大学','江西科技师范大学','南昌工程学院','井冈山大学',
        # 山东
        '德州学院','滨州学院','泰山学院','枣庄学院','菏泽学院','潍坊学院','济宁学院','山东青年政治学院','山东管理学院','山东农业工程学院',
        # 湖北
        '湖北工程学院','湖北科技学院','湖北文理学院','湖北汽车工业学院','湖北理工学院','荆楚理工学院','汉江师范学院','黄冈师范学院','武汉商学院',
        # 湖南
        '湖南科技学院','湖南人文科技学院','湖南工学院','湖南城市学院','邵阳学院','怀化学院','湘南学院','长沙师范学院','湖南女子学院',
        # 广东
        '韶关学院','惠州学院','东莞理工学院','五邑大学','肇庆学院','茂名学院','嘉应学院','广州航海学院','广东石油化工学院',
        # 广西
        '广西科技大学','桂林理工大学','桂林电子科技大学','北部湾大学','河池学院','玉林师范学院','百色学院','贺州学院','梧州学院',
        # 四川
        '绵阳师范学院','内江师范学院','宜宾学院','西昌学院','攀枝花学院','成都工业学院','四川旅游学院','成都大学',
        # 贵州
        '贵州师范大学','贵州财经大学','贵州医科大学','遵义医科大学','贵州理工学院','六盘水师范学院','安顺学院','凯里学院',
        # 陕西
        '宝鸡文理学院','咸阳师范学院','渭南师范学院','安康学院','商洛学院','榆林学院','西安航空学院','陕西学前师范学院',
        # 甘肃
        '天水师范学院','河西学院','陇东学院','甘肃民族师范学院','兰州城市学院','兰州文理学院','甘肃医学院',
        # 黑龙江
        '黑龙江科技大学','佳木斯大学','齐齐哈尔大学','牡丹江师范学院','大庆师范学院','黑河学院','绥化学院',
        # 吉林
        '北华大学','吉林师范大学','长春师范大学','通化师范学院','白城师范学院','吉林化工学院','吉林农业科技学院',
        # 辽宁
        '辽宁科技大学','辽宁工业大学','沈阳化工大学','大连交通大学','渤海大学','鞍山师范学院','辽东学院','沈阳工程学院',
        # 云南
        '曲靖师范学院','玉溪师范学院','楚雄师范学院','红河学院','文山学院','普洱学院','保山学院','昭通学院',
        # 江苏
        '淮阴师范学院','盐城师范学院','江苏理工学院','常州工学院','徐州工程学院','泰州学院','南京晓庄学院','江苏海洋大学',
        # 浙江
        '绍兴文理学院','嘉兴学院','台州学院','丽水学院','衢州学院','浙江水利水电学院','浙江外国语学院','宁波工程学院',
        # 河北
        '河北科技大学','河北建筑工程学院','河北北方学院','河北科技师范学院','唐山学院','廊坊师范学院','邢台学院','衡水学院',
        # 内蒙古
        '内蒙古科技大学','内蒙古工业大学','内蒙古民族大学','赤峰学院','呼伦贝尔学院','河套学院',
    ]
    majors = [
        # 计算机/IT类
        '计算机科学与技术(网络工程方向)','计算机科学与技术','软件工程','网络工程','物联网工程','数据科学与大数据技术','人工智能','信息安全','数字媒体技术','智能科学与技术',
        # 电子信息类
        '电子信息工程','通信工程','自动化','电气工程及其自动化','微电子科学与工程','光电信息科学与工程','电子科学与技术','机器人工程',
        # 机械/土木类
        '机械设计制造及其自动化','车辆工程','材料成型及控制工程','土木工程','建筑学','城乡规划','工程管理','工程造价',
        # 文科类
        '汉语言文学','汉语国际教育','新闻学','广告学','广播电视学','秘书学','网络与新媒体',
        # 外语类
        '英语','日语','商务英语','翻译','法语','俄语','朝鲜语',
        # 理科类
        '数学与应用数学','信息与计算科学','物理学','应用物理学','化学','应用化学','统计学','应用统计学',
        # 经济管理类
        '金融学','经济学','国际经济与贸易','会计学','财务管理','市场营销','工商管理','物流管理','电子商务','旅游管理','人力资源管理','审计学','资产评估',
        # 法学/教育类
        '法学','社会工作','思想政治教育','学前教育','小学教育','教育技术学','体育教育','运动训练',
        # 艺术/设计类
        '视觉传达设计','环境设计','产品设计','服装与服饰设计','音乐学','美术学','舞蹈学','广播电视编导','播音与主持艺术',
        # 生物/环境/化工类
        '生物科学','生物技术','生物工程','环境工程','环境科学','化学工程与工艺','制药工程','食品科学与工程','食品质量与安全',
        # 医学/护理类
        '临床医学','护理学','药学','医学检验技术','康复治疗学','口腔医学技术','医学影像技术',
        # 农林类
        '农学','园艺','动物科学','动物医学','园林','林学','水产养殖学','茶学',
        # 其他
        '地理科学','地理信息科学','心理学','应用心理学','考古学','历史学','哲学','图书馆学','档案学','公共事业管理','行政管理','劳动与社会保障','城市管理','土地资源管理',
    ]
    ethnics = ['汉族','蒙古族','回族','藏族','苗族','壮族','布依族','朝鲜族','满族','侗族','瑶族','土家族','彝族']

    # 专业→系所 映射（确保关联合理）
    major_to_dept = {
        # 计算机/IT
        '计算机科学与技术(网络工程方向)': '计算机科学与技术系',
        '计算机科学与技术': '计算机科学与技术系',
        '软件工程': '软件工程系',
        '网络工程': '网络工程系',
        '物联网工程': '电子信息工程系',
        '数据科学与大数据技术': '计算机科学与技术系',
        '人工智能': '计算机科学与技术系',
        '信息安全': '计算机科学与技术系',
        '数字媒体技术': '计算机科学与技术系',
        '智能科学与技术': '自动化系',
        # 电子信息
        '电子信息工程': '电子信息工程系',
        '通信工程': '电子信息工程系',
        '自动化': '自动化系',
        '电气工程及其自动化': '自动化系',
        '微电子科学与工程': '电子信息工程系',
        '光电信息科学与工程': '电子信息工程系',
        '电子科学与技术': '电子信息工程系',
        '机器人工程': '自动化系',
        # 机械/土木
        '机械设计制造及其自动化': '机械工程系',
        '车辆工程': '机械工程系',
        '材料成型及控制工程': '机械工程系',
        '土木工程': '土木工程系',
        '建筑学': '建筑与城市规划系',
        '城乡规划': '建筑与城市规划系',
        '工程管理': '土木工程系',
        '工程造价': '土木工程系',
        # 文科
        '汉语言文学': '人文学院',
        '汉语国际教育': '人文学院',
        '新闻学': '人文学院',
        '广告学': '人文学院',
        '广播电视学': '人文学院',
        '秘书学': '人文学院',
        '网络与新媒体': '人文学院',
        # 外语
        '英语': '外国语学院',
        '日语': '外国语学院',
        '商务英语': '外国语学院',
        '翻译': '外国语学院',
        '法语': '外国语学院',
        '俄语': '外国语学院',
        '朝鲜语': '外国语学院',
        # 理科
        '数学与应用数学': '理学院',
        '信息与计算科学': '理学院',
        '物理学': '理学院',
        '应用物理学': '理学院',
        '化学': '理学院',
        '应用化学': '理学院',
        '统计学': '理学院',
        '应用统计学': '理学院',
        # 经济管理
        '金融学': '经济管理学院',
        '经济学': '经济管理学院',
        '国际经济与贸易': '经济管理学院',
        '会计学': '经济管理学院',
        '财务管理': '经济管理学院',
        '市场营销': '经济管理学院',
        '工商管理': '经济管理学院',
        '物流管理': '经济管理学院',
        '电子商务': '经济管理学院',
        '旅游管理': '经济管理学院',
        '人力资源管理': '经济管理学院',
        '审计学': '经济管理学院',
        '资产评估': '经济管理学院',
        # 法学/教育
        '法学': '法学院',
        '社会工作': '法学院',
        '思想政治教育': '法学院',
        '学前教育': '教育学院',
        '小学教育': '教育学院',
        '教育技术学': '教育学院',
        '体育教育': '体育学院',
        '运动训练': '体育学院',
        # 艺术/设计
        '视觉传达设计': '美术与设计学院',
        '环境设计': '美术与设计学院',
        '产品设计': '美术与设计学院',
        '服装与服饰设计': '美术与设计学院',
        '音乐学': '音乐学院',
        '美术学': '美术与设计学院',
        '舞蹈学': '音乐学院',
        '广播电视编导': '人文学院',
        '播音与主持艺术': '人文学院',
        # 生物/环境/化工
        '生物科学': '生命科学学院',
        '生物技术': '生命科学学院',
        '生物工程': '生命科学学院',
        '环境工程': '环境与化学工程学院',
        '环境科学': '环境与化学工程学院',
        '化学工程与工艺': '环境与化学工程学院',
        '制药工程': '环境与化学工程学院',
        '食品科学与工程': '食品科学与工程学院',
        '食品质量与安全': '食品科学与工程学院',
        # 医学/护理
        '临床医学': '医学院',
        '护理学': '医学院',
        '药学': '医学院',
        '医学检验技术': '医学院',
        '康复治疗学': '医学院',
        '口腔医学技术': '医学院',
        '医学影像技术': '医学院',
        # 农林
        '农学': '农业与生物技术学院',
        '园艺': '农业与生物技术学院',
        '动物科学': '动物科技学院',
        '动物医学': '动物科技学院',
        '园林': '农业与生物技术学院',
        '林学': '农业与生物技术学院',
        '水产养殖学': '农业与生物技术学院',
        '茶学': '农业与生物技术学院',
        # 其他
        '地理科学': '理学院',
        '地理信息科学': '理学院',
        '心理学': '教育学院',
        '应用心理学': '教育学院',
        '考古学': '人文学院',
        '历史学': '人文学院',
        '哲学': '人文学院',
        '图书馆学': '人文学院',
        '档案学': '人文学院',
        '公共事业管理': '经济管理学院',
        '行政管理': '经济管理学院',
        '劳动与社会保障': '经济管理学院',
        '城市管理': '经济管理学院',
        '土地资源管理': '经济管理学院',
    }

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

    # 先选专业，再从映射取系所
    major = random_pick(majors)
    dept = major_to_dept.get(major, '人文学院')

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
        "major": major,
        "degree_type": "普通高等教育",
        "study_form": "普通全日制",
        "college": school,
        "dept": dept,
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
        surnames = '赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜戚谢邹喻柏水窦章云苏潘葛奚范彭郎鲁韦昌马苗凤花方俞任袁柳酆鲍史唐费廉岑薛雷贺倪汤滕殷罗毕郝邬安常乐于时傅皮卞齐康伍余元卜顾孟平黄萧程嵇邢滑裴陆荣翁荀羊於惠甄曲家封芮羿储靳汲邴糜松井段富巫乌焦巴弓牧隗山谷车侯宓蓬全郗班仰秋仲伊宫宁仇栾暴甘钭厉戎祖武符刘景詹束龙叶幸司韶郜黎蓟薄印宿白怀蒲邰从鄂索咸籍赖卓蔺屠蒙池乔阴鬱胥能苍双闻莘党翟谭贡劳逄姬申扶堵冉宰郦雍郤璩桑桂濮牛寿通边扈燕冀郏浦尚农温别庄晏柴瞿阎充慕连茹习宦艾鱼容向古易慎戈廖庾终暨居衡步都耿满弘匡国文寇广禄阙东欧殳沃利蔚越夔隆师巩厍聂晁勾敖融冷訾辛阚那简饶空曾毋沙乜养鞠须丰巢关蒯相查后荆红游竺权逯盖益桓公'
        given_names_male = ['伟','强','磊','军','勇','杰','涛','明','超','波','辉','刚','健','峰','志','国','平','斌','鑫','浩','鹏','飞','龙','海','洋','旭','阳','家豪','天宇','浩然','俊杰','宇航','志远','明辉','建华','国庆','文博','子轩','雨泽','致远','博文','思远','翰林','泽宇','瑞霖','子涵']
        given_names_female = ['芳','娜','敏','静','丽','娟','燕','玲','婷','雪','琳','萍','红','莲','英','华','秀英','志梅','桂兰','文静','美丽','淑华','秀兰','丽华','玉兰','佳怡','紫涵','梦瑶','诗涵','雨桐','语嫣','思琪','梓涵','若曦','欣怡','芷若','文君','慧敏','静怡']
        if req.gender == '男':
            sur = random.choice(surnames)
            gname = random.choice(given_names_male)
            # 随机两字或三字名
            if random.random() < 0.4:
                name = sur + random.choice(['大','小','阿','志','家','晓','永','国','文','建']) + gname[-1]
            else:
                name = sur + gname
        else:
            sur = random.choice(surnames)
            gname = random.choice(given_names_female)
            if random.random() < 0.4:
                name = sur + random.choice(['小','阿','晓','家','文','静','美']) + gname[-1]
            else:
                name = sur + gname
    info = generate_full_account(name, req.gender, req.photo)
    # 如果用户提供了身份证号，覆盖生成的，并从身份证提取出生日期
    if req.id_card and req.id_card.strip():
        cid = req.id_card.strip()
        info["id_card"] = cid
        # 身份证7-14位是出生日期 YYYYMMDD
        if len(cid) >= 14:
            y = cid[6:10]; m = cid[10:12]; d = cid[12:14]
            info["birth"] = f"{y}年{m}月{d}日"
            # 入学/离校按21岁算，不跟身份证
            enroll_year = 2026 - 21 + 18  # 2023
            grad_year = enroll_year + 4    # 2027
            info["enroll_date"] = f"{enroll_year}年09月01日"
            info["grad_date"] = f"{grad_year}年07月01日"
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

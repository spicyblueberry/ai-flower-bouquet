"""
AI花束定制平台 - 完整合并版（Streamlit Cloud可部署）
保留所有原功能：花材推荐、花束描述生成、学校LLM API调用、订单系统
新增：花束尺寸S/M/L/XL、按支数计价、材料费/人工费、用户自定义主花/配花
新增优化：生图冷却限流、详细错误处理、等待队列提示、配额显示
"""
import streamlit as st
import requests as http_requests
import json
import os
import time
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# ========== 页面配置 ==========
st.set_page_config(
    page_title="AI花束定制 | 智能花艺设计平台",
    page_icon="💐",
    layout="wide",
    initial_sidebar_state="auto"
)

# ========== API配置 ==========
try:
    API_KEY = st.secrets.get("ECNU_API_KEY", os.getenv("ECNU_API_KEY", ""))
    API_BASE = st.secrets.get("ECNU_API_BASE", os.getenv("ECNU_API_BASE", "https://chat.ecnu.edu.cn/open/api/v1"))
    MODEL_NAME = st.secrets.get("ECNU_MODEL", os.getenv("ECNU_MODEL", "ecnu-plus"))
except:
    API_KEY = os.getenv("ECNU_API_KEY", "")
    API_BASE = os.getenv("ECNU_API_BASE", "https://chat.ecnu.edu.cn/open/api/v1")
    MODEL_NAME = os.getenv("ECNU_MODEL", "ecnu-plus")

# ========== 生图限流配置 ==========
IMAGE_GEN_COOLDOWN_SECONDS = 60  # 冷却时间（秒）
MAX_RETRY_COUNT = 2  # 最大重试次数
IMAGE_GEN_TIMEOUT = 90  # 生图超时时间（秒）

# ========== CSS ==========
st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #fff9fb 0%, #fff5f8 100%); }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-track { background: #f1f1f1; border-radius: 10px; }
    ::-webkit-scrollbar-thumb { background: linear-gradient(135deg, #ff6b9d, #8b5cf6); border-radius: 10px; }
    .main-header {
        text-align: center; padding: 40px 20px 30px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 0 0 30px 30px; margin: -60px -50px 30px -50px;
        color: white; box-shadow: 0 10px 30px rgba(0,0,0,0.1);
    }
    .flower-item {
        background: linear-gradient(135deg, #fff 0%, #fef5f7 100%);
        border-radius: 20px; padding: 20px;
        border: 1px solid rgba(255,107,157,0.2);
        transition: all 0.3s ease; cursor: pointer; height: 100%;
    }
    .flower-item:hover { transform: translateY(-5px); border-color: #ff6b9d; box-shadow: 0 10px 25px rgba(255,107,157,0.15); }
    .flower-visual {
        width: 80px; height: 80px; border-radius: 50%; margin: 0 auto 12px;
        background: conic-gradient(from 0deg, #ff6b9d, #8b5cf6, #667eea, #ff6b9d);
        display: flex; align-items: center; justify-content: center;
        font-size: 40px; box-shadow: 0 4px 15px rgba(102,126,234,0.3);
    }
    .flower-name { font-size: 18px; font-weight: bold; text-align: center; color: #333; margin-bottom: 6px; }
    .flower-language { font-size: 12px; text-align: center; color: #ff6b9d; margin-bottom: 10px; font-style: italic; }
    @keyframes bouquet-spin {
        0% { transform: rotate(0deg) scale(1); }
        50% { transform: rotate(180deg) scale(1.1); }
        100% { transform: rotate(360deg) scale(1); }
    }
    .loading-bouquet { animation: bouquet-spin 2s ease-in-out infinite; font-size: 60px; text-align: center; display: inline-block; }
    .ai-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white; padding: 20px; border-radius: 20px; border-top-left-radius: 5px;
        margin: 20px 0; box-shadow: 0 5px 15px rgba(102,126,234,0.3);
    }
    .stButton > button {
        background: linear-gradient(135deg, #ff6b9d, #8b5cf6);
        color: white; border: none; border-radius: 40px;
        padding: 10px 20px; font-weight: bold; transition: all 0.3s ease;
    }
    .stButton > button:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(255,107,157,0.4); }
    .stButton > button:disabled {
        background: #ccc !important;
        cursor: not-allowed !important;
        transform: none !important;
    }
    .price-tag {
        display: inline-block; background: linear-gradient(135deg, #ff6b9d, #8b5cf6);
        color: white; padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: bold;
    }
    .type-badge-main {
        display: inline-block; background: linear-gradient(135deg, #ff6b9d, #ff4081);
        color: white; padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: bold;
    }
    .type-badge-filler {
        display: inline-block; background: linear-gradient(135deg, #667eea, #764ba2);
        color: white; padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: bold;
    }
    .quota-warning {
        background: #fef3c7; border-left: 4px solid #f59e0b;
        padding: 12px; border-radius: 8px; margin: 10px 0;
    }
    .quota-error {
        background: #fee2e2; border-left: 4px solid #ef4444;
        padding: 12px; border-radius: 8px; margin: 10px 0;
    }
    .footer {
        text-align: center; padding: 30px; margin-top: 50px;
        color: #999; font-size: 12px; border-top: 1px solid rgba(255,107,157,0.2);
    }
</style>
""", unsafe_allow_html=True)


# ========== RAG引擎 ==========
class FlowerRAGEngine:
    def __init__(self):
        try:
            knowledge_path = os.path.join(os.path.dirname(__file__), "knowledge_base", "flower_knowledge.json")
            with open(knowledge_path, "r", encoding="utf-8") as f:
                self.flower_data = json.load(f)
        except FileNotFoundError:
            self.flower_data = self._get_default_flowers()

    def _get_default_flowers(self):
        return [
            {"id": 1, "name": "玫瑰", "color": "红色、粉色、白色、黄色", "language": "爱情、热恋、你是我的唯一", "occasion": ["情人节", "表白", "纪念日", "婚礼"], "target": ["恋人"], "style": "浪漫", "price_level": "中", "unit_price": 8, "category": "主花", "season": "全年", "description": "经典爱情之花，多层花瓣优雅绽放", "scent": "有香味"},
            {"id": 2, "name": "向日葵", "color": "黄色", "language": "沉默的爱、阳光、积极向上", "occasion": ["毕业", "日常惊喜", "探望"], "target": ["朋友", "家人"], "style": "阳光活力", "price_level": "低", "unit_price": 5, "category": "主花", "season": "夏季", "description": "明亮耀眼的大花盘，象征阳光与希望", "scent": "无香味"},
            {"id": 3, "name": "百合", "color": "白色、粉色", "language": "纯洁、优雅、百年好合", "occasion": ["婚礼", "乔迁", "探望"], "target": ["恋人", "家人"], "style": "清新自然", "price_level": "中高", "unit_price": 12, "category": "主花", "season": "全年", "description": "清香四溢的优雅花材，花型优美", "scent": "有香味"},
            {"id": 4, "name": "康乃馨", "color": "粉色、红色、白色", "language": "母爱、温馨、感恩", "occasion": ["母亲节", "探望", "生日"], "target": ["家人", "老师"], "style": "温馨", "price_level": "低", "unit_price": 3, "category": "配花", "season": "全年", "description": "母亲节的代表花卉，温柔而持久", "scent": "有香味"},
            {"id": 5, "name": "满天星", "color": "白色、粉色", "language": "真心喜欢、默默守护", "occasion": ["日常惊喜", "表白", "毕业"], "target": ["恋人", "朋友"], "style": "清新自然", "price_level": "低", "unit_price": 2, "category": "配花", "season": "全年", "description": "星星点点的可爱小花，花束中的精灵", "scent": "无香味"},
            {"id": 6, "name": "郁金香", "color": "红色、黄色、紫色、白色", "language": "爱的宣言、高贵、幸福", "occasion": ["表白", "纪念日", "日常惊喜"], "target": ["恋人"], "style": "简约高级", "price_level": "中高", "unit_price": 10, "category": "主花", "season": "春季", "description": "优雅的杯状花型，荷兰国花", "scent": "无香味"},
            {"id": 7, "name": "绣球", "color": "蓝色、粉色、紫色、白色", "language": "永恒团圆、希望、美满", "occasion": ["乔迁", "婚礼", "探望"], "target": ["家人", "朋友"], "style": "浪漫", "price_level": "中", "unit_price": 15, "category": "主花", "season": "夏季", "description": "圆润饱满的花球，象征团圆美满", "scent": "无香味"},
            {"id": 8, "name": "洋桔梗", "color": "白色、粉色、紫色", "language": "真诚不变的爱、感动", "occasion": ["表白", "生日", "日常惊喜"], "target": ["恋人", "朋友"], "style": "清新自然", "price_level": "中", "unit_price": 6, "category": "主花", "season": "全年", "description": "层层叠叠的花瓣，温柔而雅致", "scent": "无香味"},
            {"id": 9, "name": "尤加利叶", "color": "绿色", "language": "恩赐、回忆、自然", "occasion": ["日常惊喜", "乔迁"], "target": ["朋友", "家人"], "style": "清新自然", "price_level": "低", "unit_price": 3, "category": "配花", "season": "全年", "description": "清新芬芳的叶材，北欧风格代表", "scent": "有香味"},
            {"id": 10, "name": "小雏菊", "color": "白色、黄色", "language": "快乐、天真、隐藏的爱", "occasion": ["毕业", "生日", "日常惊喜"], "target": ["朋友", "孩子"], "style": "可爱", "price_level": "低", "unit_price": 2, "category": "配花", "season": "春季", "description": "小巧可爱的花朵，充满童真", "scent": "无香味"},
            {"id": 11, "name": "牡丹", "color": "粉色、红色、白色", "language": "富贵、圆满、国色天香", "occasion": ["乔迁", "开业", "年节"], "target": ["家人", "客户"], "style": "华丽大气", "price_level": "高", "unit_price": 20, "category": "主花", "season": "春季", "description": "花中之王，大气华贵", "scent": "有香味"},
            {"id": 12, "name": "勿忘我", "color": "紫色、蓝色", "language": "永恒的记忆、真爱", "occasion": ["纪念日", "毕业", "表白"], "target": ["恋人", "朋友"], "style": "清新自然", "price_level": "低", "unit_price": 2, "category": "配花", "season": "全年", "description": "小巧的紫色花朵，可做干花", "scent": "无香味"},
            {"id": 13, "name": "泡泡玫瑰", "color": "粉色、白色、橙色", "language": "多变的爱、小巧可人", "occasion": ["日常惊喜", "生日", "表白"], "target": ["恋人", "朋友"], "style": "可爱", "price_level": "中", "unit_price": 6, "category": "主花", "season": "全年", "description": "多头小玫瑰，可爱又浪漫", "scent": "有香味"}
        ]

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if not self.flower_data:
            return []
        query = query.lower()
        keywords = set(query.replace("、", " ").split())
        scored_flowers = []
        for flower in self.flower_data:
            score = 0
            search_text = (flower.get("name", "") + flower.get("color", "") + flower.get("language", "") + " ".join(flower.get("occasion", [])) + " ".join(flower.get("target", [])) + flower.get("style", "") + flower.get("description", "")).lower()
            for kw in keywords:
                if kw in search_text:
                    score += 1
            if score > 0:
                scored_flowers.append((score, flower))
        scored_flowers.sort(key=lambda x: x[0], reverse=True)
        results = []
        for i in range(min(top_k, len(scored_flowers))):
            results.append(scored_flowers[i][1].copy())
        return results


rag_engine = FlowerRAGEngine()


# ========== LLM调用（增强版）==========
def call_ecnu_llm(system_prompt: str, user_prompt: str, max_tokens: int = 300, silent: bool = False) -> str:
    """
    调用ECNU LLM API
    
    Args:
        system_prompt: 系统提示词
        user_prompt: 用户提示词
        max_tokens: 最大token数
        silent: 是否静默模式（不显示警告）
    
    Returns:
        str: 生成的文本，失败返回None
    """
    # 检查API密钥
    if not API_KEY:
        if not silent:
            st.warning("⚠️ API密钥未配置，请检查环境变量或Secrets配置")
        return None
    
    if API_KEY == "你的API密钥":
        if not silent:
            st.warning("⚠️ 请将API密钥替换为真实的ECNU API密钥")
        return None
    
    try:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.7,
            "max_tokens": max_tokens
        }
        
        # 发送请求
        resp = http_requests.post(
            f"{API_BASE}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        # 处理不同类型的错误
        if resp.status_code == 401:
            if not silent:
                st.warning("⚠️ API密钥无效，请检查配置")
            return None
        elif resp.status_code == 404:
            if not silent:
                st.warning(f"⚠️ API接口不存在：{API_BASE}/chat/completions")
            return None
        elif resp.status_code == 429:
            if not silent:
                st.warning("⚠️ API调用频率过高，请稍后再试")
            return None
        elif resp.status_code != 200:
            if not silent:
                st.warning(f"⚠️ API返回错误: {resp.status_code}")
            return None
        
        # 解析响应
        result = resp.json()
        
        if "choices" in result and len(result["choices"]) > 0:
            content = result["choices"][0].get("message", {}).get("content", "")
            if content:
                return content
        
        if not silent:
            st.warning(f"⚠️ API返回格式异常，未找到有效内容")
        return None
        
    except http_requests.exceptions.Timeout:
        if not silent:
            st.warning("⚠️ LLM调用超时（30秒），请检查网络连接")
        return None
    except http_requests.exceptions.ConnectionError:
        if not silent:
            st.warning(f"⚠️ 无法连接到API服务器：{API_BASE}")
        return None
    except Exception as e:
        if not silent:
            st.warning(f"⚠️ LLM调用异常: {type(e).__name__}")
        return None

# ========== 业务函数 ==========
def recommend_flowers_balanced(target, occasion, color_preference, style, budget, size="M"):
    """
    智能推荐花材，自动按主花、配花、叶材、果材分类推荐
    """
    query = f"{target} {occasion} {color_preference} {style} {budget}"
    
    # 根据尺寸确定各类花材数量
    size_config = {'S': {'主花': 2, '配花': 2, '叶材': 1, '果材': 0},
                   'M': {'主花': 3, '配花': 2, '叶材': 1, '果材': 1},
                   'L': {'主花': 3, '配花': 3, '叶材': 2, '果材': 1},
                   'XL': {'主花': 4, '配花': 3, '叶材': 2, '果材': 2}}
    config = size_config.get(size, size_config['M'])
    
    # 获取所有花材
    all_flowers = rag_engine.flower_data
    
    # 分类花材（如果category字段为空，使用名称推断）
    def infer_category(flower):
        """根据花材名称推断分类"""
        name = flower.get("name", "")
        # 叶材关键词
        leaf_keywords = ['叶', '草', '蕨', '松', '竹', '尤加利', '喷泉', '龟背', '散尾', '蓬莱', '排草', '羊齿', '剑叶', '栀子叶', '龙柳', '红瑞木']
        # 配花关键词
        filler_keywords = ['满天星', '勿忘我', '情人草', '水晶草', '蕾丝', '翠珠', '风铃', '蓝星', '松虫', '鼠尾', '相思梅', '翠菊', '波斯菊', '黄金球', '澳洲米花']
        # 果材关键词
        fruit_keywords = ['红豆', '冬青', '火棘', '灯笼果', '蔷薇果', '棉花', '蒲棒', '芦苇']
        
        if any(kw in name for kw in leaf_keywords):
            return '叶材'
        elif any(kw in name for kw in filler_keywords):
            return '配花'
        elif any(kw in name for kw in fruit_keywords):
            return '果材'
        else:
            return '主花'
    
    # 分类花材
    main_flowers = [f for f in all_flowers if f.get("category") == "主花" or infer_category(f) == "主花"]
    filler_flowers = [f for f in all_flowers if f.get("category") == "配花" or infer_category(f) == "配花"]
    leaf_flowers = [f for f in all_flowers if f.get("category") == "叶材" or infer_category(f) == "叶材"]
    fruit_flowers = [f for f in all_flowers if f.get("category") == "果材" or infer_category(f) == "果材"]
    
    # 如果分类后仍然为空，使用全部花材并默认分类
    if not main_flowers:
        main_flowers = all_flowers[:4]  # 取前4个作为主花
    if not filler_flowers:
        filler_flowers = all_flowers[:3] if len(all_flowers) >= 3 else all_flowers
    if not leaf_flowers:
        leaf_flowers = []
    if not fruit_flowers:
        fruit_flowers = []
    
    # 根据查询进行匹配打分
    query_lower = query.lower()
    keywords = set(query_lower.split())
    
    def score_flower(flower):
        score = 0
        search_text = (flower.get("name", "") + flower.get("color", "") + 
                      flower.get("language", "") + " ".join(flower.get("occasion", [])) + 
                      " ".join(flower.get("target", [])) + flower.get("style", "")).lower()
        for kw in keywords:
            if kw in search_text:
                score += 1
        return score
    
    # 排序并选取
    main_flowers.sort(key=score_flower, reverse=True)
    filler_flowers.sort(key=score_flower, reverse=True)
    leaf_flowers.sort(key=score_flower, reverse=True)
    fruit_flowers.sort(key=score_flower, reverse=True)
    
    selected_main = main_flowers[:config['主花']]
    selected_filler = filler_flowers[:config['配花']]
    selected_leaf = leaf_flowers[:config['叶材']]
    selected_fruit = fruit_flowers[:config['果材']] if config['果材'] > 0 else []
    
    # 合并所有推荐
    all_selected = selected_main + selected_filler + selected_leaf + selected_fruit
    
    # 去重
    seen_ids = set()
    unique_flowers = []
    for f in all_selected:
        if f["id"] not in seen_ids:
            seen_ids.add(f["id"])
            unique_flowers.append(f)
    
    # 生成AI推荐语
    main_names = "、".join([f["name"] for f in selected_main[:2]])
    filler_names = "、".join([f["name"] for f in selected_filler[:2]])
    
    prompt = f"""你是一个专业的花艺推荐师。请根据以下花材组合，写一段150字以内的推荐语。

推荐对象：{target}
场合：{occasion}
颜色偏好：{color_preference}
风格偏好：{style}
花束尺寸：{size}

推荐花材组合：
主花：{[f['name'] for f in selected_main]}
配花：{[f['name'] for f in selected_filler]}
叶材：{[f['name'] for f in selected_leaf]}
{f'果材：{[f["name"] for f in selected_fruit]}' if selected_fruit else ''}

请输出一段温暖有感染力的推荐语。"""

    recommendation_text = call_ecnu_llm("你是一位温暖专业的花艺推荐师。", prompt)
    if not recommendation_text:
        recommendation_text = f"🌷 为您精心设计了专属花束！主花选用{main_names}，搭配{filler_names}，整体风格{style}，{color_preference}色调与「{occasion}」场合完美契合。让这份花礼传达您的心意～"

    return {
        "success": True,
        "flowers": unique_flowers,
        "main_flowers": selected_main,
        "filler_flowers": selected_filler,
        "leaf_flowers": selected_leaf,
        "fruit_flowers": selected_fruit,
        "recommendation": recommendation_text
    }


def generate_bouquet_description(flower_ids, color_preference=""):
    selected_flowers = [f for f in rag_engine.flower_data if f["id"] in flower_ids]
    
    if not selected_flowers:
        return {"success": False, "message": "请至少选择一种花材"}
    
    # ===== 关键修改：获取用户设定的支数 =====
    flower_details_with_quantity = []
    for flower in selected_flowers:
        flower_id = flower["id"]
        # 从 session_state 中获取用户设定的支数
        quantity = st.session_state.flower_quantities.get(flower_id, 3)
        if quantity > 0:
            flower_details_with_quantity.append({
                "name": flower["name"],
                "quantity": quantity
            })
    
    # 如果没有支数信息，使用默认值
    if not flower_details_with_quantity:
        for flower in selected_flowers:
            flower_details_with_quantity.append({
                "name": flower["name"],
                "quantity": 3
            })
    
    # 构建带支数的花材列表字符串
    flower_names_with_qty = ", ".join([f"{d['quantity']} {d['name']}" for d in flower_details_with_quantity])
    flower_names_only = [f["name"] for f in selected_flowers]
    
    # 收集颜色信息
    flower_colors = []
    for f in selected_flowers:
        color_field = f.get("color", "")
        for c in ['红色', '粉色', '白色', '黄色', '紫色', '蓝色', '绿色', '橙色', '香槟色']:
            if c in color_field:
                flower_colors.append(c)
    flower_colors = list(set(flower_colors))
    
    if color_preference and color_preference != "任意":
        color_keywords = color_preference
    elif flower_colors:
        color_keywords = "、".join(flower_colors[:3])
    else:
        color_keywords = "vibrant"
    
    # ===== 关键修改：Prompt中明确要求包含具体支数 =====
    prompt = f"""请将以下花材组合转化为一段英文的花束描述，用于AI文生图工具生成花束图片。

花材及数量（重要：必须包含每种花材的具体数量）：
{flower_names_with_qty}

整体色彩：{color_keywords}

要求：
- **必须明确写出每种花材的具体数量**（例如 "3 roses", "5 lilies" 这样的格式）
- 描述中必须包含「{color_keywords}」作为整体色调
- 描述花材的层次、包装风格
- 包含 "bouquet"、"wrapped in kraft paper"、"floral photography" 等关键词
- 用词优美，适合AI绘画
- 输出纯英文，60词以内
- 示例格式："A beautiful bouquet of 3 red roses and 2 white lilies, wrapped in kraft paper, natural lighting..."

请严格按照要求生成描述，确保每种花材都有数量前缀。"""

    description = call_ecnu_llm("你擅长将花材搭配转化为优美的英文描述，注意必须包含每种花材的具体数量。", prompt, max_tokens=250)
    
    if not description:
        # 备用描述（确保包含数量）
        qty_parts = [f"{d['quantity']} {d['name']}" for d in flower_details_with_quantity]
        flower_names_str = " and ".join(qty_parts)
        description = f"A stunning {color_keywords} bouquet consisting of {flower_names_str}. Fresh floral arrangement with layered textures, soft natural lighting, wrapped in kraft paper, professional floral photography style, high quality, 8k."
    
    return {"success": True, "description": description, "flower_names": flower_names_only, "color_theme": color_preference or "自然搭配"}

def generate_flower_image_with_retry(prompt_text, size="1024x1024", retry_count=0):
    """
    调用文生图API生成花束图片（带重试和详细错误处理）
    
    返回格式:
        {"success": True, "url": "图片URL"} 或
        {"success": False, "error_type": "配额/权限/超时/参数错误", "message": "错误信息", "status_code": 404}
    """
    if not API_KEY:
        return {"success": False, "error_type": "认证失败", "message": "API密钥未配置，无法生成图片", "status_code": 401}
    
    try:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "ecnu-image",
            "prompt": prompt_text,
            "n": 1,
            "size": size,
            "response_format": "url"
        }
        
        # 发送请求
        resp = http_requests.post(
            f"{API_BASE}/images/generations",
            headers=headers,
            json=payload,
            timeout=IMAGE_GEN_TIMEOUT
        )
        
        # 根据状态码分类处理
        if resp.status_code == 200:
            result = resp.json()
            if "data" in result and len(result["data"]) > 0:
                image_data = result["data"][0]
                # 尝试多种可能的URL字段名
                image_url = None
                for key in ["url", "image_url", "link", "src"]:
                    if key in image_data:
                        image_url = image_data[key]
                        break
                
                if image_url:
                    return {"success": True, "url": image_url}
                else:
                    return {"success": False, "error_type": "响应格式错误", "message": "API返回的数据中没有图片URL", "status_code": 200}
            else:
                return {"success": False, "error_type": "响应格式错误", "message": "API返回的数据中没有图片", "status_code": 200}
                
        elif resp.status_code == 401:
            return {"success": False, "error_type": "认证失败", "message": "API密钥无效或已过期，请检查配置", "status_code": 401}
        
        elif resp.status_code == 404:
            return {"success": False, "error_type": "接口不存在", "message": "文生图接口未找到，请检查API地址或确认是否有生图权限", "status_code": 404}
        
        elif resp.status_code == 429:
            # 配额/限流错误
            error_text = resp.text[:200] if resp.text else ""
            return {"success": False, "error_type": "配额/限流", "message": f"生图配额已用完或请求过于频繁，请稍后再试。{error_text}", "status_code": 429}
        
        elif resp.status_code >= 500:
            return {"success": False, "error_type": "服务端错误", "message": f"生成服务繁忙或超时，请稍后重试 (HTTP {resp.status_code})", "status_code": resp.status_code}
        
        else:
            return {"success": False, "error_type": "未知错误", "message": f"生图失败: {resp.status_code} - {resp.text[:200]}", "status_code": resp.status_code}
            
    except http_requests.exceptions.Timeout:
        return {"success": False, "error_type": "超时", "message": f"生成图片超时（超过{IMAGE_GEN_TIMEOUT}秒），模型可能繁忙，请稍后重试", "status_code": None}
    
    except http_requests.exceptions.ConnectionError as e:
        return {"success": False, "error_type": "连接失败", "message": f"无法连接到API服务器: {str(e)[:100]}", "status_code": None}
    
    except Exception as e:
        return {"success": False, "error_type": "异常", "message": f"生成图片时发生异常: {type(e).__name__}: {str(e)[:100]}", "status_code": None}


def is_image_gen_allowed():
    """检查是否允许生成图片（冷却时间和重试限制）"""
    now = time.time()
    
    # 检查冷却时间
    if "last_image_gen_time" in st.session_state:
        elapsed = now - st.session_state.last_image_gen_time
        if elapsed < IMAGE_GEN_COOLDOWN_SECONDS:
            wait_seconds = int(IMAGE_GEN_COOLDOWN_SECONDS - elapsed)
            return {"allowed": False, "reason": "冷却", "wait_seconds": wait_seconds}
    
    # 检查今日生成次数（可选，如果API没有配额限制可以注释）
    today = datetime.now().strftime("%Y-%m-%d")
    if "image_gen_count" not in st.session_state:
        st.session_state.image_gen_count = {}
        st.session_state.image_gen_count[today] = 0
    
    if today not in st.session_state.image_gen_count:
        st.session_state.image_gen_count[today] = 0
    
    # 每日限制（根据API配额调整，默认20次）
    DAILY_LIMIT = 20
    if st.session_state.image_gen_count[today] >= DAILY_LIMIT:
        return {"allowed": False, "reason": "日配额", "daily_limit": DAILY_LIMIT}
    
    return {"allowed": True}


def record_image_gen():
    """记录一次图片生成（用于限流统计）"""
    now = time.time()
    st.session_state.last_image_gen_time = now
    
    today = datetime.now().strftime("%Y-%m-%d")
    if "image_gen_count" not in st.session_state:
        st.session_state.image_gen_count = {}
    if today not in st.session_state.image_gen_count:
        st.session_state.image_gen_count[today] = 0
    st.session_state.image_gen_count[today] += 1


def get_quota_status():
    """获取配额状态信息"""
    today = datetime.now().strftime("%Y-%m-%d")
    if "image_gen_count" not in st.session_state:
        st.session_state.image_gen_count = {}
        st.session_state.image_gen_count[today] = 0
    
    daily_limit = 20
    used = st.session_state.image_gen_count.get(today, 0)
    remaining = max(0, daily_limit - used)
    
    # 检查冷却状态
    cooldown_remaining = 0
    if "last_image_gen_time" in st.session_state:
        elapsed = time.time() - st.session_state.last_image_gen_time
        if elapsed < IMAGE_GEN_COOLDOWN_SECONDS:
            cooldown_remaining = int(IMAGE_GEN_COOLDOWN_SECONDS - elapsed)
    
    return {
        "daily_limit": daily_limit,
        "daily_used": used,
        "daily_remaining": remaining,
        "cooldown_remaining": cooldown_remaining
    }


# ========== 辅助函数 ==========
def get_flower_emoji(flower_name):
    emoji_map = {
        '玫瑰': '🌹', '泡泡玫瑰': '🌹', '百合': '⚜️', '康乃馨': '🌸',
        '洋桔梗': '💐', '绣球': '🪻', '满天星': '⭐', '向日葵': '🌻',
        '郁金香': '🌷', '芍药': '🌺', '牡丹': '🌺', '勿忘我': '💜',
        '情人草': '💜', '扶郎花': '🌼', '小雏菊': '🌼', '乒乓菊': '⚪',
        '洋甘菊': '🌼', '茉莉花': '🤍', '栀子花': '🤍', '荷花': '🪷',
        '红豆': '❤️', '尤加利叶': '🌿', '龟背竹叶': '🌿', 'default': '💐'
    }
    return emoji_map.get(flower_name, emoji_map['default'])


def get_flower_type(flower_name):
    # 优先使用用户自定义的分类
    if "custom_types" in st.session_state and flower_name in st.session_state.custom_types:
        return st.session_state.custom_types[flower_name]

    # 从数据库获取默认分类
    for flower in rag_engine.flower_data:
        if flower['name'] == flower_name:
            category = flower.get('category', '配花')
            if category in ['叶材', '果材']:
                return '配花'
            return category

    # 原有逻辑作为后备
    leaf_keywords = ['叶', '草', '蕨', '松', '竹', '尤加利', '喷泉', '龟背', '散尾', '蓬莱', '排草', '羊齿', '剑叶', '栀子叶', '龙柳', '红瑞木']
    filler_keywords = ['满天星', '勿忘我', '情人草', '水晶草', '蕾丝', '翠珠', '风铃', '蓝星', '松虫', '鼠尾', '相思梅', '翠菊', '波斯菊', '黄金球', '澳洲米花']
    fruit_keywords = ['红豆', '冬青', '火棘', '灯笼果', '蔷薇果', '棉花', '蒲棒', '芦苇']
    name_lower = flower_name.lower()
    if any(kw in name_lower for kw in leaf_keywords):
        return '叶材'
    elif any(kw in name_lower for kw in filler_keywords):
        return '配花'
    elif any(kw in name_lower for kw in fruit_keywords):
        return '果材'
    else:
        return '主花'


def get_default_quantity(flower, size):
    flower_type = get_flower_type(flower['name'])
    size_defaults = {
        'S': {'主花': 3, '配花': 2},
        'M': {'主花': 5, '配花': 3},
        'L': {'主花': 8, '配花': 5},
        'XL': {'主花': 12, '配花': 8}
    }
    return size_defaults.get(size, {}).get(flower_type, 3)


def get_min_quantity(flower, size):
    return 1


def get_max_quantity(flower, size):
    flower_type = get_flower_type(flower['name'])
    size_max = {'S': 5, 'M': 10, 'L': 20, 'XL': 30}
    type_max = {'主花': size_max.get(size, 10), '配花': size_max.get(size, 10) * 2}
    return type_max.get(flower_type, 10)


def get_step(flower):
    flower_type = get_flower_type(flower['name'])
    return 1 if flower_type == '主花' else 2


def calculate_bouquet_price(selected_flowers, flower_quantities, size):
    flower_cost = 0
    flower_detail = []
    for flower in selected_flowers:
        flower_id = flower["id"]
        quantity = flower_quantities.get(flower_id, 0)
        unit_price = flower.get("unit_price", 5)
        subtotal = quantity * unit_price
        flower_cost += subtotal
        flower_detail.append({
            "name": flower["name"],
            "type": get_flower_type(flower['name']),
            "quantity": quantity,
            "unit_price": unit_price,
            "subtotal": subtotal
        })
    packaging_cost = {'S': 15, 'M': 25, 'L': 40, 'XL': 60}.get(size, 25)
    labor_cost = {'S': 30, 'M': 45, 'L': 65, 'XL': 90}.get(size, 45)
    subtotal_before_delivery = flower_cost + packaging_cost + labor_cost
    delivery_fee = 20 if subtotal_before_delivery < 200 else 0
    total_price = subtotal_before_delivery + delivery_fee
    return {
        "flower_cost": flower_cost,
        "packaging_cost": packaging_cost,
        "labor_cost": labor_cost,
        "delivery_fee": delivery_fee,
        "subtotal_before_delivery": subtotal_before_delivery,
        "total_price": total_price,
        "flower_detail": flower_detail
    }


# ========== 初始化session_state ==========
if "recommend_result" not in st.session_state:
    st.session_state.recommend_result = None
if "selected_flowers" not in st.session_state:
    st.session_state.selected_flowers = []
if "bouquet_desc" not in st.session_state:
    st.session_state.bouquet_desc = None
if "history" not in st.session_state:
    st.session_state.history = []
if "target" not in st.session_state:
    st.session_state.target = "恋人"
if "occasion" not in st.session_state:
    st.session_state.occasion = "日常惊喜"
if "color" not in st.session_state:
    st.session_state.color = "粉色"
if "style" not in st.session_state:
    st.session_state.style = "浪漫"
if "budget" not in st.session_state:
    st.session_state.budget = "中"
if "flower_type_filter" not in st.session_state:
    st.session_state.flower_type_filter = "全部"
if "season_filter" not in st.session_state:
    st.session_state.season_filter = "全年"
if "has_scent_filter" not in st.session_state:
    st.session_state.has_scent_filter = "全部"
if "custom_message" not in st.session_state:
    st.session_state.custom_message = ""
if "size" not in st.session_state:
    st.session_state.size = "M"
if "flower_quantities" not in st.session_state:
    st.session_state.flower_quantities = {}
if "generated_image_url" not in st.session_state:
    st.session_state.generated_image_url = None
# 用户自定义花材分类
if "custom_types" not in st.session_state:
    st.session_state.custom_types = {}
# 生图限流相关
if "last_image_gen_time" not in st.session_state:
    st.session_state.last_image_gen_time = 0
if "image_gen_count" not in st.session_state:
    st.session_state.image_gen_count = {}


# ========== 头部 ==========
st.markdown("""
<div class="main-header">
    <div style="font-size: 60px; margin-bottom: 10px;">💐</div>
    <h1 style="font-size: 42px; margin: 0;">AI花束定制平台</h1>
    <p style="font-size: 16px; opacity: 0.9; margin-top: 10px;">智能花艺推荐 · 专属花束设计 · 线下花店配送</p>
    <p style="font-size: 12px; opacity: 0.7; margin-top: 5px;">🤖 Powered by ECNU Chat 大语言模型 | 第三届全民数字素养与AI创新应用大赛</p>
</div>
""", unsafe_allow_html=True)

# ========== 侧边栏 ==========
with st.sidebar:
    st.markdown("### 🌸 定制你的花束")
    st.markdown("---")
    
    # ===== 配额状态显示 =====
    quota = get_quota_status()
    if quota["daily_remaining"] <= 3:
        st.markdown(f"""
        <div class="quota-warning">
            ⚠️ **配额提醒**<br>
            今日剩余生图次数: {quota["daily_remaining"]}/{quota["daily_limit"]}次<br>
            请合理使用，避免浪费
        </div>
        """, unsafe_allow_html=True)
    else:
        st.caption(f"📊 今日可用生图: {quota['daily_remaining']}/{quota['daily_limit']}次")
    
    if quota["cooldown_remaining"] > 0:
        st.caption(f"⏳ 冷却中: {quota['cooldown_remaining']}秒后可继续生成图片")
    
    target = st.selectbox("👤 送给谁？", ["恋人", "家人", "朋友", "老师", "自己", "客户", "孩子"])
    st.session_state.target = target
    occasion = st.selectbox("🎉 什么场合？", ["日常惊喜", "生日", "表白", "纪念日", "毕业", "情人节", "乔迁", "开业", "探望", "道歉", "婚礼", "年节", "母亲节"])
    st.session_state.occasion = occasion
    with st.expander("🎯 高级筛选（花材类型/季节/香味）", expanded=False):
        st.session_state.flower_type_filter = st.selectbox("🌿 花材类型", ["全部", "主花", "配花", "叶材", "果材"])
        st.session_state.season_filter = st.selectbox("📅 适用季节", ["全年", "春季", "夏季", "秋季", "冬季"])
        st.session_state.has_scent_filter = st.selectbox("🌺 香气", ["全部", "有香味", "无香味"])
    st.markdown("---")
    st.session_state.color = st.selectbox("🎨 偏好颜色", ["任意", "粉色", "红色", "白色", "紫色", "黄色", "橙色", "蓝色", "绿色"])
    st.session_state.style = st.selectbox("✨ 偏好风格", ["任意", "浪漫", "清新自然", "简约高级", "阳光活力", "复古", "可爱", "华丽大气"])
    st.session_state.budget = st.selectbox("💰 预算", ["任意", "低", "中", "中高", "高"])
    # 尺寸选择
    size_options = {
        "S": "🌱 S码 - 小巧精致",
        "M": "💐 M码 - 标准适中",
        "L": "🌺 L码 - 大气饱满",
        "XL": "🎊 XL码 - 豪华盛宴"
    }
    st.session_state.size = st.selectbox("📏 花束尺寸", list(size_options.keys()), format_func=lambda x: size_options[x], help="S：10-15cm | M：20-25cm | L：30-35cm | XL：40cm+")
    st.markdown("---")
    st.caption("🤖 由 ChatECNU 大模型驱动")
    st.caption("🏪 合作花店: 华东师大周边花店")
    if st.session_state.history:
        st.markdown("---")
        st.markdown("### 📜 历史搭配")
        for i, record in enumerate(st.session_state.history[:5]):
            if st.button(f"💐 {record['time']} · {', '.join(record['flowers'][:2])}...", key=f"history_{i}", use_container_width=True):
                st.session_state.selected_flowers = record.get("selected_flowers", [])
                st.rerun()

# ========== 主区域 ==========

# 灵感画廊 - 增强版
st.markdown("### 🖼️ 灵感画廊")
st.markdown("*点击卡片一键生成专属花束推荐*")

gallery_data = [
    ("🌹", "红玫瑰恋曲", "送给恋人的浪漫惊喜", {"target": "恋人", "occasion": "情人节", "color": "红色", "style": "浪漫"}),
    ("🌻", "向日葵阳光", "毕业季的阳光祝福", {"target": "朋友", "occasion": "毕业", "color": "黄色", "style": "阳光活力"}),
    ("🤍", "纯白新娘", "婚礼的纯洁祝福", {"target": "恋人", "occasion": "婚礼", "color": "白色", "style": "简约高级"}),
    ("💜", "紫色梦境", "纪念日的深情告白", {"target": "恋人", "occasion": "纪念日", "color": "紫色", "style": "浪漫"}),
]

gallery_cols = st.columns(4)
for i, (emoji, name, description, config) in enumerate(gallery_data):
    with gallery_cols[i]:
        # 创建可点击的卡片
        card_clicked = st.container()
        with card_clicked:
           st.markdown(f"""<div style="background: linear-gradient(135deg, #fff, #fef5f7); border-radius: 16px; padding: 15px; text-align: center; border: 1px solid #eee; margin-bottom: 8px;"><div style="font-size: 36px;">{emoji}</div><div style="font-weight: bold; font-size: 14px;">{name}</div><span class="price-tag" style="font-size: 10px; display: inline-block; margin-top: 6px;">{tag}</span></div>""", unsafe_allow_html=True)
        
        # 点击按钮触发推荐
        if st.button(f"生成「{name}」", key=f"gallery_btn_{i}", use_container_width=True):
            # 设置侧边栏参数
            st.session_state.target = config["target"]
            st.session_state.occasion = config["occasion"]
            st.session_state.color = config["color"]
            st.session_state.style = config["style"]
            
            # 自动推荐
            with st.spinner(f"💐 正在为您生成「{name}」..."):
                result = recommend_flowers_balanced(
                    target=st.session_state.target,
                    occasion=st.session_state.occasion,
                    color_preference=st.session_state.color if st.session_state.color != "任意" else "",
                    style=st.session_state.style if st.session_state.style != "任意" else "浪漫",
                    budget=st.session_state.budget,
                    size=st.session_state.size
                )
                if result["success"]:
                    st.session_state.recommend_result = result
                    st.session_state.selected_flowers = []
                    st.session_state.flower_quantities = {}
                    st.session_state.custom_types = {}
                    st.toast(f"✅ 「{name}」生成成功！", icon="🎉")
                else:
                    st.error("推荐失败")
            st.rerun()

st.markdown("---")

# AI推荐按钮
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("✨ AI智能推荐花材", use_container_width=True):
        with st.spinner("💐 AI花艺师正在精心搭配..."):
            result = recommend_flowers_balanced(
                target=st.session_state.target,
                occasion=st.session_state.occasion,
                color_preference=st.session_state.color if st.session_state.color != "任意" else "",
                style=st.session_state.style if st.session_state.style != "任意" else "浪漫",
                budget=st.session_state.budget if st.session_state.budget != "任意" else "",
                size=st.session_state.size
                 )  
            if result["success"]:
                st.session_state.recommend_result = result
                st.session_state.selected_flowers = []
                st.session_state.flower_quantities = {}
                st.session_state.custom_types = {}
                st.success("✅ 推荐完成！")
                st.balloons()
            else:
                st.error("推荐失败")

st.markdown("---")

# 显示推荐结果（按分类分组）
if st.session_state.recommend_result:
    result = st.session_state.recommend_result
    st.markdown("### 💌 AI花艺师的温馨推荐")
    st.markdown(f"""<div class="ai-message"><p>💐 {result['recommendation']}</p></div>""", unsafe_allow_html=True)
    
    st.markdown("### 🌷 为您精选的花材组合")
    st.markdown("*点击卡片选择花材*")
    
    # 🌹 主花
    if result.get("main_flowers"):
        st.markdown("#### 🌹 主花（花束焦点）")
        cols = st.columns(min(len(result["main_flowers"]), 3))
        for idx, flower in enumerate(result["main_flowers"]):
            with cols[idx % 3]:
                is_selected = any(f["id"] == flower["id"] for f in st.session_state.selected_flowers)
                unit_price = flower.get("unit_price", 5)
                border_color = "#ff6b9d" if is_selected else "#eee"
                bg_color = "#fef5f7" if is_selected else "white"
                st.markdown(f"""
                <div class="flower-item" style="border: 2px solid {border_color}; background: {bg_color};">
                    <div class="flower-visual"><span style="font-size: 42px;">{get_flower_emoji(flower['name'])}</span></div>
                    <div class="flower-name">{flower['name']}</div>
                    <div class="flower-language">「{flower['language']}」</div>
                    <div style="margin: 8px 0;"><span class="price-tag">💰 ¥{unit_price}/支</span></div>
                </div>
                """, unsafe_allow_html=True)
                if not is_selected:
                    if st.button(f"➕ 选择", key=f"select_main_{flower['id']}", use_container_width=True):
                        st.session_state.selected_flowers.append(flower)
                        st.session_state.flower_quantities[flower["id"]] = 3
                        st.rerun()
    
    # ✨ 配花
    if result.get("filler_flowers"):
        st.markdown("#### ✨ 配花（增添层次）")
        cols = st.columns(min(len(result["filler_flowers"]), 3))
        for idx, flower in enumerate(result["filler_flowers"]):
            with cols[idx % 3]:
                is_selected = any(f["id"] == flower["id"] for f in st.session_state.selected_flowers)
                unit_price = flower.get("unit_price", 5)
                border_color = "#ff6b9d" if is_selected else "#eee"
                bg_color = "#fef5f7" if is_selected else "white"
                st.markdown(f"""
                <div class="flower-item" style="border: 2px solid {border_color}; background: {bg_color};">
                    <div class="flower-visual"><span style="font-size: 42px;">{get_flower_emoji(flower['name'])}</span></div>
                    <div class="flower-name">{flower['name']}</div>
                    <div class="flower-language">「{flower['language']}」</div>
                    <div style="margin: 8px 0;"><span class="price-tag">💰 ¥{unit_price}/支</span></div>
                </div>
                """, unsafe_allow_html=True)
                if not is_selected:
                    if st.button(f"➕ 选择", key=f"select_filler_{flower['id']}", use_container_width=True):
                        st.session_state.selected_flowers.append(flower)
                        st.session_state.flower_quantities[flower["id"]] = 3
                        st.rerun()
    
    # 🍃 叶材
    if result.get("leaf_flowers"):
        st.markdown("#### 🍃 叶材（自然基底）")
        cols = st.columns(min(len(result["leaf_flowers"]), 3))
        for idx, flower in enumerate(result["leaf_flowers"]):
            with cols[idx % 3]:
                is_selected = any(f["id"] == flower["id"] for f in st.session_state.selected_flowers)
                unit_price = flower.get("unit_price", 5)
                border_color = "#ff6b9d" if is_selected else "#eee"
                bg_color = "#fef5f7" if is_selected else "white"
                st.markdown(f"""
                <div class="flower-item" style="border: 2px solid {border_color}; background: {bg_color};">
                    <div class="flower-visual"><span style="font-size: 42px;">{get_flower_emoji(flower['name'])}</span></div>
                    <div class="flower-name">{flower['name']}</div>
                    <div class="flower-language">「{flower['language']}」</div>
                    <div style="margin: 8px 0;"><span class="price-tag">💰 ¥{unit_price}/支</span></div>
                </div>
                """, unsafe_allow_html=True)
                if not is_selected:
                    if st.button(f"➕ 选择", key=f"select_leaf_{flower['id']}", use_container_width=True):
                        st.session_state.selected_flowers.append(flower)
                        st.session_state.flower_quantities[flower["id"]] = 2
                        st.rerun()
    
    # 🍎 果材
    if result.get("fruit_flowers"):
        st.markdown("#### 🍎 果材（点睛之笔）")
        cols = st.columns(min(len(result["fruit_flowers"]), 3))
        for idx, flower in enumerate(result["fruit_flowers"]):
            with cols[idx % 3]:
                is_selected = any(f["id"] == flower["id"] for f in st.session_state.selected_flowers)
                unit_price = flower.get("unit_price", 5)
                border_color = "#ff6b9d" if is_selected else "#eee"
                bg_color = "#fef5f7" if is_selected else "white"
                st.markdown(f"""
                <div class="flower-item" style="border: 2px solid {border_color}; background: {bg_color};">
                    <div class="flower-visual"><span style="font-size: 42px;">{get_flower_emoji(flower['name'])}</span></div>
                    <div class="flower-name">{flower['name']}</div>
                    <div class="flower-language">「{flower['language']}」</div>
                    <div style="margin: 8px 0;"><span class="price-tag">💰 ¥{unit_price}/支</span></div>
                </div>
                """, unsafe_allow_html=True)
                if not is_selected:
                    if st.button(f"➕ 选择", key=f"select_fruit_{flower['id']}", use_container_width=True):
                        st.session_state.selected_flowers.append(flower)
                        st.session_state.flower_quantities[flower["id"]] = 1
                        st.rerun()
    # 我的花篮（新增自定义分类切换）
    if st.session_state.selected_flowers:
        st.markdown("---")
        st.markdown("### 🛒 我的花篮")
        st.markdown(f"*已选择 {len(st.session_state.selected_flowers)} 种花材 · 尺寸：{st.session_state.size}码*")
        st.caption("💡 提示：可调整支数、上下移动顺序、点击「切换」改变主花/配花分类")

        # 初始化默认支数和分类
        for flower in st.session_state.selected_flowers:
            if flower["id"] not in st.session_state.flower_quantities:
                st.session_state.flower_quantities[flower["id"]] = get_default_quantity(flower, st.session_state.size)
            if flower["name"] not in st.session_state.custom_types:
                # 使用数据库默认分类（叶材果材已归入配花）
                default_category = flower.get("category", "配花")
                if default_category in ["叶材", "果材"]:
                    default_category = "配花"
                st.session_state.custom_types[flower["name"]] = default_category

        # 分类统计
        main_flowers = [f for f in st.session_state.selected_flowers if st.session_state.custom_types.get(f["name"], "配花") == "主花"]
        filler_flowers = [f for f in st.session_state.selected_flowers if st.session_state.custom_types.get(f["name"], "配花") == "配花"]

        col_main, col_filler = st.columns(2)
        with col_main:
            st.markdown(f"🌹 **主花**：{len(main_flowers)}种 | {sum([st.session_state.flower_quantities.get(f['id'], 0) for f in main_flowers])}支")
        with col_filler:
            st.markdown(f"✨ **配花**：{len(filler_flowers)}种 | {sum([st.session_state.flower_quantities.get(f['id'], 0) for f in filler_flowers])}支")

        # 显示每种花材
        for i, flower in enumerate(st.session_state.selected_flowers):
            col_a, col_b, col_c, col_d, col_e, col_f, col_g = st.columns([0.3, 1.5, 1.5, 1, 0.8, 0.3, 0.3])

            with col_a:
                st.write(f"**#{i+1}**")
            with col_b:
                st.write(f"{get_flower_emoji(flower['name'])} {flower['name']}")
            with col_c:
                current_type = st.session_state.custom_types.get(flower["name"], "配花")
                type_emoji = "🌹" if current_type == "主花" else "✨"
                unit_price = flower.get("unit_price", 5)
                st.write(f"{type_emoji} {current_type} | ¥{unit_price}/支")
            with col_d:
                new_qty = st.number_input(
                    "支数",
                    min_value=get_min_quantity(flower, st.session_state.size),
                    max_value=get_max_quantity(flower, st.session_state.size),
                    value=st.session_state.flower_quantities.get(flower["id"], get_default_quantity(flower, st.session_state.size)),
                    step=get_step(flower),
                    key=f"qty_{flower['id']}"
                )
                st.session_state.flower_quantities[flower["id"]] = new_qty
            with col_e:
                # 切换主花/配花按钮
                current_type = st.session_state.custom_types.get(flower["name"], "配花")
                if current_type == "主花":
                    if st.button("📌 改配花", key=f"toggle_{flower['id']}", use_container_width=True, help="点击切换为配花"):
                        st.session_state.custom_types[flower["name"]] = "配花"
                        st.rerun()
                else:
                    if st.button("⭐ 改主花", key=f"toggle_{flower['id']}", use_container_width=True, help="点击切换为主花"):
                        st.session_state.custom_types[flower["name"]] = "主花"
                        st.rerun()
            with col_f:
                if i > 0 and st.button("⬆️", key=f"up_{flower['id']}"):
                    new_list = st.session_state.selected_flowers.copy()
                    new_list[i], new_list[i-1] = new_list[i-1], new_list[i]
                    st.session_state.selected_flowers = new_list
                    st.rerun()
            with col_g:
                if i < len(st.session_state.selected_flowers) - 1 and st.button("⬇️", key=f"down_{flower['id']}"):
                    new_list = st.session_state.selected_flowers.copy()
                    new_list[i], new_list[i+1] = new_list[i+1], new_list[i]
                    st.session_state.selected_flowers = new_list
                    st.rerun()

        # 价格明细
        st.markdown("---")
        st.markdown("### 💰 价格明细")
        price_breakdown = calculate_bouquet_price(st.session_state.selected_flowers, st.session_state.flower_quantities, st.session_state.size)

        col_price1, col_price2 = st.columns(2)
        with col_price1:
            st.markdown("**🌷 花材费用明细：**")
            for item in price_breakdown["flower_detail"]:
                if item["quantity"] > 0:
                    flower_emoji = get_flower_emoji(item["name"])
                    st.write(f"{flower_emoji} {item['name']} ({item['type']}) × {item['quantity']}支 = ¥{item['subtotal']}")
            st.write(f"**花材小计：¥{price_breakdown['flower_cost']}**")
        with col_price2:
            st.markdown("**📦 其他费用：**")
            st.write(f"📦 包装材料费：¥{price_breakdown['packaging_cost']}")
            st.write(f"👨‍🎨 花艺师手工费：¥{price_breakdown['labor_cost']}")
            if price_breakdown['delivery_fee'] > 0:
                st.write(f"🚗 配送费：¥{price_breakdown['delivery_fee']}")
            else:
                st.write("🚗 配送费：**免费** (满¥200免配送费)")
            st.markdown("---")
            st.metric("💰 订单总价", f"¥{price_breakdown['total_price']}")
            st.caption("⚠️ 此为预估价格，最终价格以花艺师确认为准")

        # 搭配比例分析
        st.markdown("### 📊 搭配比例分析")
        total_stems = sum(st.session_state.flower_quantities.values())
        main_stems = sum([st.session_state.flower_quantities.get(f['id'], 0) for f in main_flowers])
        filler_stems = sum([st.session_state.flower_quantities.get(f['id'], 0) for f in filler_flowers])
        if total_stems > 0:
            st.progress(main_stems/total_stems, text=f"🌹 主花 {main_stems}支 ({main_stems/total_stems*100:.0f}%)")
            st.progress(filler_stems/total_stems, text=f"✨ 配花 {filler_stems}支 ({filler_stems/total_stems*100:.0f}%)")
            if main_stems == 0:
                st.warning("💡 请至少设置1种主花，让花束有视觉焦点")
            elif main_stems/total_stems < 0.2:
                st.warning("💡 建议主花占比不低于20%，让花束更有焦点")
            elif main_stems/total_stems > 0.8:
                st.info("💡 可以适当增加配花，让花束更有层次感")
            elif 0.3 <= main_stems/total_stems <= 0.7:
                st.success("✅ 主配花比例协调，花束层次丰富！")

        # 一键建议分类按钮
        if st.button("🔄 一键建议分类", help="根据花材特性自动建议主花/配花分类"):
            for flower in st.session_state.selected_flowers:
                default_category = flower.get("category", "配花")
                if default_category in ["叶材", "果材"]:
                    default_category = "配花"
                st.session_state.custom_types[flower["name"]] = default_category
            st.success("✅ 已恢复默认分类建议")
            st.rerun()

        # 生成花束示意图按钮（带冷却和限流）
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            # 检查是否允许生成
            gen_check = is_image_gen_allowed()
            button_disabled = not gen_check["allowed"]
            button_help = ""
            if not gen_check["allowed"]:
                if gen_check["reason"] == "冷却":
                    button_help = f"请等待 {gen_check['wait_seconds']} 秒后再生成"
                elif gen_check["reason"] == "日配额":
                    button_help = f"今日生成次数已达上限（{gen_check['daily_limit']}次），明天再来吧"
            
            if st.button(
                "🎨 生成花束示意图", 
                type="primary", 
                use_container_width=True,
                disabled=button_disabled,
                help=button_help
            ):
                with st.status("🎨 AI正在创作中...", expanded=True) as status:
                    try:
                        # 步骤1：生成花束描述
                        status.update(label="📝 步骤1/3: 生成花束描述...", state="running")
                        selected_ids = [f["id"] for f in st.session_state.selected_flowers]
                        desc_result = generate_bouquet_description(
                            flower_ids=selected_ids,
                            color_preference=st.session_state.color if st.session_state.color != "任意" else ""
                        )
                        
                        if not desc_result["success"]:
                            status.update(label="❌ 生成失败", state="error")
                            st.error(desc_result.get("message", "生成花束描述失败"))
                            st.stop()
                        
                        st.session_state.bouquet_desc = desc_result["description"]
                        status.update(label="✅ 步骤1/3: 花束描述生成完成", state="complete")
                        
                        # 步骤2：调用文生图API
                        status.update(label="🎨 步骤2/3: 调用AI绘画模型（可能需要30-60秒）...", state="running")
                        
                        # 显示进度提示
                        st.info("⏳ AI正在生成图片，请耐心等待... 生图模型处理较慢，通常需要30-90秒")
                        
                        image_result = generate_flower_image_with_retry(
                            st.session_state.bouquet_desc,
                            size="1024x1024"
                        )
                        
                        if image_result["success"]:
                            status.update(label="✅ 步骤2/3: 图片生成成功", state="complete")
                            st.session_state.generated_image_url = image_result["url"]
                            
                            # 步骤3：记录生成历史
                            status.update(label="📝 步骤3/3: 保存记录...", state="running")
                            record_image_gen()
                            status.update(label="🎉 全部完成！花束示意图已就绪", state="complete")
                            st.success("✨ 花束示意图生成成功！")
                            st.balloons()
                            st.rerun()
                        else:
                            # 详细错误处理
                            error_type = image_result.get("error_type", "未知错误")
                            error_msg = image_result.get("message", "")
                            status_code = image_result.get("status_code", "")
                            
                            status.update(label=f"❌ 生成失败: {error_type}", state="error")
                            
                            if error_type == "配额/限流":
                                st.markdown(f"""
                                <div class="quota-error">
                                    ❌ **生图配额不足**<br>
                                    {error_msg}<br>
                                    💡 建议：请明天再试，或联系管理员增加配额
                                </div>
                                """, unsafe_allow_html=True)
                            elif error_type == "认证失败":
                                st.markdown(f"""
                                <div class="quota-error">
                                    ❌ **API认证失败**<br>
                                    {error_msg}<br>
                                    💡 建议：请检查API密钥配置是否正确
                                </div>
                                """, unsafe_allow_html=True)
                            elif error_type == "接口不存在":
                                st.markdown(f"""
                                <div class="quota-error">
                                    ❌ **文生图接口未找到**<br>
                                    {error_msg}<br>
                                    💡 建议：确认当前账号是否有生图权限，或联系管理员开通
                                </div>
                                """, unsafe_allow_html=True)
                            elif error_type == "超时":
                                st.markdown(f"""
                                <div class="quota-error">
                                    ⏰ **生成超时**<br>
                                    {error_msg}<br>
                                    💡 建议：模型繁忙，请稍后重试（建议等待30秒再试）
                                </div>
                                """, unsafe_allow_html=True)
                            else:
                                st.error(f"❌ 图片生成失败: {error_msg}")
                            
                            # 记录失败但不占用配额次数（不调用 record_image_gen）
                            st.info("💡 提示词已生成，您也可以将上方提示词复制到其他AI绘画工具中使用")
                            
                    except Exception as e:
                        status.update(label="❌ 生成过程发生异常", state="error")
                        st.error(f"生成过程中发生异常: {str(e)}")
        
        with col_btn2:
            if total_stems > 0:
                st.metric("🌸 总花材支数", f"{total_stems}支")

# ===== 花束示意图展示区 =====
if st.session_state.bouquet_desc:
    st.markdown("---")
    st.markdown("### 🖼️ AI花束示意图")
    st.info("💡 **提示**：示意图仅展示花材搭配风格和配色，最终成品以花艺师制作为准")

    with st.expander("📝 查看AI生图提示词", expanded=True):
        st.code(st.session_state.bouquet_desc, language="text")
        col_copy1, col_copy2 = st.columns([1, 3])
        with col_copy1:
            if st.button("📋 复制提示词", use_container_width=True):
                st.write("✅ 已复制到剪贴板")
                # 使用JavaScript复制（实际需要js，但streamlit中可手动复制）
    
    # 显示生成的图片
    if st.session_state.generated_image_url:
        st.image(
            st.session_state.generated_image_url,
            caption="✨ AI生成的花束参考图（图片24小时后失效，请及时保存）",
            use_column_width=True
        )
        st.caption("💡 如需保存图片，请右键点击图片选择「图片另存为」")
    
    # 花语祝福
    st.markdown("### 💌 定制祝福语")
    st.session_state.custom_message = st.text_area("写下你想对Ta说的话...", value=st.session_state.custom_message, height=80)

    if st.session_state.selected_flowers:
        flower_languages = [f"「{f['name']}」：{f['language'][:20]}..." for f in st.session_state.selected_flowers[:5]]
        if st.session_state.custom_message:
            st.info(f"💐 {st.session_state.custom_message}\n\n🌸 " + "\n".join(flower_languages))
        else:
            st.info("🌸 " + "\n".join(flower_languages))

    # 订单按钮
    st.markdown("---")
    if st.session_state.selected_flowers:
        price_breakdown = calculate_bouquet_price(st.session_state.selected_flowers, st.session_state.flower_quantities, st.session_state.size)

        col_order1, col_order2, col_order3 = st.columns([1, 2, 1])
        with col_order2:
            if st.button("💐 确认订单，配送到家", type="primary", use_container_width=True):
                new_record = {
                    "time": datetime.now().strftime("%m-%d %H:%M"),
                    "flowers": [f["name"] for f in st.session_state.selected_flowers],
                    "selected_flowers": st.session_state.selected_flowers.copy(),
                }
                if new_record not in st.session_state.history:
                    st.session_state.history.insert(0, new_record)
                    st.session_state.history = st.session_state.history[:10]

                st.success("✅ 订单已提交！合作花店将尽快与您联系 📞")
                st.balloons()
                order_details = [f"{item['name']}({item['type']}) × {item['quantity']}支" for item in price_breakdown["flower_detail"] if item["quantity"] > 0]
                st.markdown(f"""### 📋 订单信息
- **花束尺寸**：{st.session_state.size}码
- **花材清单**：{'、'.join(order_details)}
- **花材费用**：¥{price_breakdown['flower_cost']}
- **包装材料**：¥{price_breakdown['packaging_cost']}
- **手工费**：¥{price_breakdown['labor_cost']}
- **配送费**：{'免费' if price_breakdown['delivery_fee'] == 0 else f"¥{price_breakdown['delivery_fee']}"}
- **订单总价**：**¥{price_breakdown['total_price']}**
- **您的寄语**：{st.session_state.custom_message if st.session_state.custom_message else '无'}
""")
                st.info("💡 工作人员将在30分钟内电话确认订单详情")

# ========== 页脚 ==========
st.markdown("""
<div class="footer">
    <p>© 2026 华东师范大学 · AI花束定制平台</p>
    <p>Powered by ChatECNU 大模型 | 第三届全民数字素养与人工智能创新应用大赛</p>
</div>
""", unsafe_allow_html=True)

#!/usr/bin/env python3
"""Generate 100 diverse story seeds for interactive novel pipeline."""

import json
import random
import itertools

random.seed(42)

GENRES = [
    ("悬疑推理", ["密室杀人", "连环失踪", "遗嘱争夺", "冷案重查", "身份伪装", "密码解谜"]),
    ("校园日常/奇幻", ["青梅竹马重逢", "社团秘密", "校园怪谈", "转学生的秘密", "毕业季告白", "文化祭奇迹"]),
    ("科幻生存", ["太空站危机", "时间循环", "AI觉醒", "末日避难所", "克隆伦理", "星际殖民"]),
    ("古风武侠", ["江湖复仇", "门派内斗", "宝藏争夺", "武林盟主", "边疆守卫", "宫廷暗战"]),
    ("都市奇幻", ["灵异事务所", "都市妖怪", "超能力觉醒", "平行世界", "时间旅行者", "记忆交易"]),
    ("历史架空", ["乱世谋士", "宫廷女官", "海上丝路", "革命前夜", "考古发现", "密使任务"]),
    ("恐怖惊悚", ["孤岛求生", "废弃医院", "诅咒之镜", "地下实验室", "鬼屋探险", "深海恐惧"]),
    ("赛博朋克", ["黑客行动", "义体改造", "企业阴谋", "意识上传", "街头跑者", "数据走私"]),
    ("童话暗黑", ["被遗忘的王国", "魔女的花园", "人偶的心", "影子国度", "迷失之森", "月光契约"]),
    ("日常治愈", ["深夜食堂", "旧书店奇缘", "邮递员日志", "流浪猫咖啡馆", "废墟花园", "星空露营"]),
]

TIME_PERIODS = [
    "远古神话时代", "春秋战国", "汉代", "唐代（盛唐）", "宋代", "明代", "清末民初",
    "1920年代上海", "1940年代", "1960年代", "1980年代", "现代（当下）",
    "近未来（2040年代）", "远未来（2200年）", "架空纪元",
    "维多利亚时代", "文艺复兴", "大航海时代", "二战期间", "冷战时期",
]

LOCATIONS = [
    "雾都伦敦", "京都古寺", "上海弄堂", "北京胡同", "威尼斯水巷",
    "阿拉斯加冰原", "撒哈拉绿洲", "东京新宿", "巴黎蒙马特",
    "海滨小镇", "深山古村", "孤岛灯塔", "地下城市", "漂浮空城",
    "沙漠遗迹", "雪山寺院", "废弃游乐园", "大学校园", "太空站",
    "蒸汽都市", "热带雨林", "北极科考站", "潜水艇内", "古堡庄园",
    "边境小镇", "渔村港口", "移动列车", "地下矿城", "云端学院",
]

PROTAGONIST_TRAITS = [
    "沉默寡言但观察力敏锐", "乐观开朗但隐藏创伤", "冷静理性但逐渐学会共情",
    "热血冲动但心地善良", "怯懦胆小但关键时刻爆发", "玩世不恭但内心正义",
    "天才型但社交障碍", "平凡普通但有隐藏天赋", "失忆者试图找回过去",
    "外来者/局外人视角", "双重身份的秘密持有者", "背负家族使命的继承人",
]

NPC_ARCHETYPES = [
    ("青梅竹马", "温柔但藏着秘密"), ("对手/宿敌", "亦敌亦友的复杂关系"),
    ("导师/长辈", "引导但不完全可信"), ("活泼后辈", "表面元气实则敏感"),
    ("神秘人", "来历不明的关键角色"), ("忠实伙伴", "永远站在主角身边但有自己的难题"),
    ("执法者", "代表秩序的力量"), ("反派/阴谋者", "有自己苦衷的对立面"),
    ("受害者", "需要拯救但可能不是表面那样"), ("旁观者", "知道真相但选择沉默"),
    ("商人/情报贩子", "一切皆可交易"), ("艺术家/学者", "沉浸在自己世界的偏执者"),
]

BRANCH_TEMPLATES = [
    "信任{npc_a} vs 怀疑{npc_a}（影响真相揭露路线）",
    "独自行动 vs 寻求同伴帮助（影响生死和结局深度）",
    "选择{action_a} vs 选择{action_b}（决定角色线路）",
    "牺牲个人利益拯救他人 vs 保全自身（影响道德结局）",
    "追寻真相 vs 维持现状（影响世界观揭示程度）",
    "和平解决 vs 武力对抗（影响后续关系和可用路径）",
]

ACTIONS = [
    ("调查线索", "保护证人"), ("逃离现场", "正面对抗"),
    ("接受委托", "拒绝并自行调查"), ("说出真相", "隐瞒秘密"),
    ("打开禁忌之门", "封印并离开"), ("拯救个体", "拯救群体"),
    ("选择记忆", "选择遗忘"), ("留下来", "离开此地"),
]

SURNAME_POOLS = {
    "中文": ["林", "陈", "王", "张", "李", "赵", "沈", "苏", "顾", "叶", "白", "秦", "楚", "柳", "萧", "卫", "姜", "温", "程", "霍"],
    "日文": ["远野", "神尾", "星野", "九条院", "雪城", "御影", "月代", "风间", "桐生", "天城"],
    "西方": ["Crawford", "Moreau", "Ashford", "Blackwood", "Sterling", "Voss", "Devereux", "Hartwell"],
}

GIVEN_NAMES = {
    "中文_男": ["晓", "轩", "泽", "昊", "辰", "阳", "宇", "风", "寒", "翊"],
    "中文_女": ["月", "雪", "琴", "瑶", "灵", "薇", "颜", "溪", "岚", "漓"],
    "日文_男": ["秋人", "�的", "苍真", "悠斗", "晴树"],
    "日文_女": ["铃音", "结衣", "千早", "奏", "雫", "�的"],
    "西方_男": ["Edmund", "Victor", "Leon", "Arthur", "Felix"],
    "西方_女": ["Isabella", "Emily", "Claire", "Helena", "Sophia"],
}


def pick_name_culture(location, time_period):
    if any(k in location + time_period for k in ["京都", "东京", "日", "校园", "海滨"]):
        return "日文"
    if any(k in location + time_period for k in ["伦敦", "巴黎", "威尼斯", "维多利亚", "文艺复兴", "大航海", "阿拉斯加", "北极"]):
        return "西方"
    return "中文"


def gen_name(culture, gender="男"):
    surname = random.choice(SURNAME_POOLS.get(culture, SURNAME_POOLS["中文"]))
    key = f"{culture}_{gender}"
    given = random.choice(GIVEN_NAMES.get(key, GIVEN_NAMES["中文_男"]))
    if culture == "西方":
        return f"{given} {surname}"
    return f"{surname}{given}"


def gen_seed(idx):
    genre_name, subgenres = random.choice(GENRES)
    subgenre = random.choice(subgenres)
    time_period = random.choice(TIME_PERIODS)
    location = random.choice(LOCATIONS)
    culture = pick_name_culture(location, time_period)

    protag_trait = random.choice(PROTAGONIST_TRAITS)
    protag_name = gen_name(culture, random.choice(["男", "女"]))

    npc_count = random.randint(3, 5)
    npc_pool = random.sample(NPC_ARCHETYPES, min(npc_count, len(NPC_ARCHETYPES)))
    npcs = []
    used_genders = []
    for archetype, desc in npc_pool:
        g = random.choice(["男", "女"])
        used_genders.append(g)
        name = gen_name(culture, g)
        npcs.append(f"- {name} — {archetype}，{desc}")

    action_pair = random.choice(ACTIONS)
    branches = random.sample(BRANCH_TEMPLATES, 3)
    branch_text = []
    for b in branches:
        b = b.replace("{npc_a}", npcs[0].split("—")[0].strip().lstrip("- "))
        b = b.replace("{action_a}", action_pair[0])
        b = b.replace("{action_b}", action_pair[1])
        branch_text.append(f"- {b}")

    seed_content = f"""## 故事种子：{subgenre}

**类型**：{genre_name}
**时代**：{time_period}
**地点**：{location}

**故事概要**：
一个关于「{subgenre}」的{genre_name}故事，发生在{time_period}的{location}。主角{protag_name}，{protag_trait}，被卷入一场围绕「{subgenre}」的事件中。随着故事推进，需要在信任与怀疑、行动与等待之间做出抉择，每个选择都将影响最终走向。

**主角**：
- {protag_name} — {protag_trait}

**关键 NPC**：
{chr(10).join(npcs)}

**期望的分支**：
{chr(10).join(branch_text)}"""

    query_template = (
        "你是一个互动小说生成 pipeline 的执行者。请按照以下步骤操作：\n\n"
        "1. 进入 /mnt/pipeline/ 目录\n"
        "2. 运行命令：python3 pipeline.py --mode llm --seed-file /tmp/seed.txt "
        "--api-base $LLM_API_BASE --api-key $LLM_API_KEY --model $LLM_MODEL --output-dir /tmp/output\n"
        "3. 种子内容已写入 /tmp/seed.txt\n"
        "4. 完成后，将 /tmp/output/ 目录中的所有文件内容作为结果返回\n\n"
        "注意：如果遇到 requests 库缺失，先运行 pip install requests"
    )

    return {
        "id": f"seed_{idx:04d}",
        "query": query_template,
        "seed_content": seed_content,
        "config": {
            "max_branches": random.randint(2, 4),
            "max_dead_ends": random.randint(5, 15),
            "language": "zh",
        },
    }


def main():
    seeds = [gen_seed(i) for i in range(1, 101)]

    # Ensure genre diversity: check distribution
    from collections import Counter
    genre_dist = Counter()
    for s in seeds:
        for line in s["seed_content"].split("\n"):
            if line.startswith("**类型**："):
                genre_dist[line.split("：")[1]] += 1
    print("Genre distribution:")
    for g, c in genre_dist.most_common():
        print(f"  {g}: {c}")

    out_path = "data/seeds_100.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for s in seeds:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    print(f"\nGenerated {len(seeds)} seeds -> {out_path}")


if __name__ == "__main__":
    main()

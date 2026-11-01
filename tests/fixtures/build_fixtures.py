"""オフライン確認用のサンプルデータを生成する（架空の論文です）。

python tests/fixtures/build_fixtures.py
"""
import json
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).parent

# (id, published, title, abstract, comment, journal_ref, categories)
PAPERS = [
    ("2610.21001", "2026-10-30T17:59:01Z", "BiFlow-VLA: Bimanual Vision-Language-Action Policies with Flow Matching",
     "We present BiFlow-VLA, a vision-language-action model for bimanual manipulation trained with flow matching on 12k teleoperated demonstrations. On 10 real-world tasks with two 7-DoF arms, BiFlow-VLA improves success rate by 18 points over prior VLA baselines while running at 30 Hz. Code is available at https://github.com/example/biflow-vla.",
     "Accepted to CoRL 2026. Project page: https://example.github.io/biflow", "", ["cs.RO", "cs.LG"]),
    ("2610.21002", "2026-10-30T15:20:00Z", "Latent World Models for Contact-Rich Assembly",
     "We study whether latent world models can plan contact-rich assembly. Our model predicts future tactile and visual latents and is trained entirely in simulation. Experiments in simulation show 2x sample efficiency over model-free RL.",
     "Submitted to ICRA 2027", "", ["cs.RO"]),
    ("2610.21003", "2026-10-29T12:00:00Z", "Whole-Body Humanoid Teleoperation from a Single RGB Camera",
     "We propose a low-cost teleoperation system that retargets human whole-body motion captured by a single RGB camera to a humanoid robot. We collect 500 demonstrations and train imitation policies that walk and manipulate boxes on a real humanoid.",
     "", "", ["cs.RO", "cs.CV"]),
    ("2610.21004", "2026-10-29T09:00:00Z", "TactileDiff: Diffusion Policies with GelSight Feedback for In-Hand Reorientation",
     "TactileDiff conditions a diffusion policy on high-resolution tactile images for in-hand object reorientation with a 16-DoF dexterous hand. Real-robot experiments on 20 unseen objects show 76% success.",
     "8 pages, 6 figures", "", ["cs.RO"]),
    ("2610.21005", "2026-10-28T18:00:00Z", "OpenNav-Bench: A Benchmark for Language-Guided Navigation in Homes",
     "We release OpenNav-Bench, a benchmark of 3,000 language-guided navigation episodes across 60 scanned homes, and evaluate 12 foundation-model agents.",
     "NeurIPS 2026 Datasets and Benchmarks Track (accepted)", "", ["cs.CV", "cs.RO"]),
    ("2610.21006", "2026-10-27T10:00:00Z", "Sim-to-Real Transfer of Agile Quadruped Parkour via Teacher-Student Distillation",
     "We train a quadruped parkour policy in simulation with privileged information and distill it into a depth-based student. The policy transfers zero-shot to a real quadruped and climbs 0.5 m obstacles.",
     "", "", ["cs.RO", "cs.LG"]),
    ("2610.21007", "2026-10-26T08:00:00Z", "Scaling Laws for Robot Foundation Models",
     "We train 40 robot foundation models from 10M to 3B parameters on a mixture of 1M robot trajectories and find power-law scaling of success rate with data and model size.",
     "", "", ["cs.LG", "cs.RO"]),
    ("2610.21008", "2026-10-24T08:00:00Z", "Safe Human-Robot Handover with Predictive Intent Models",
     "We present a handover controller that predicts human intent from gaze and hand pose and adjusts robot motion to keep separation distance. A user study with 24 participants shows reduced handover time.",
     "", "", ["cs.RO", "cs.HC"]),
    ("2610.21009", "2026-10-21T08:00:00Z", "Occupancy World Models for Autonomous Driving",
     "We propose a 4D occupancy world model that forecasts scene evolution for autonomous driving and improves planning on nuScenes.",
     "", "IEEE Robotics and Automation Letters, 2026", ["cs.CV", "cs.RO"]),
    ("2606.11001", "2026-06-10T08:00:00Z", "pi-Next: A Generalist Robot Policy",
     "We introduce a generalist vision-language-action policy trained on diverse robot data that performs long-horizon household tasks on multiple real robot embodiments.",
     "Accepted at RSS 2026", "", ["cs.RO", "cs.LG"]),
    ("2603.09001", "2026-03-05T08:00:00Z", "Diffusion Policy 2: Fast and Robust Visuomotor Policy Learning",
     "We revisit diffusion-based visuomotor policies and propose a faster sampler that runs at 100 Hz on real robots while improving robustness.",
     "", "", ["cs.RO"]),
    ("2610.21010", "2026-10-31T11:00:00Z", "Learning Dexterous Grasping from Human Videos",
     "We learn dexterous grasping policies from internet human videos by retargeting hand poses, achieving 60% grasp success on unseen objects with a real multi-fingered hand.",
     "", "", ["cs.RO", "cs.CV"]),
]


def build_xml():
    entries = []
    for pid, pub, title, abs_, comment, jref, cats in PAPERS:
        cat_xml = "".join(f'<category term="{c}" scheme="http://arxiv.org/schemas/atom"/>' for c in cats)
        entries.append(f"""<entry>
<id>http://arxiv.org/abs/{pid}v1</id><updated>{pub}</updated><published>{pub}</published>
<title>{escape(title)}</title><summary>{escape(abs_)}</summary>
<author><name>Taro Example</name></author><author><name>Jane Doe</name></author>
{f'<arxiv:comment>{escape(comment)}</arxiv:comment>' if comment else ''}
{f'<arxiv:journal_ref>{escape(jref)}</arxiv:journal_ref>' if jref else ''}
<link href="http://arxiv.org/abs/{pid}v1" rel="alternate" type="text/html"/>
<link title="pdf" href="http://arxiv.org/pdf/{pid}v1" rel="related" type="application/pdf"/>
<arxiv:primary_category term="{cats[0]}" scheme="http://arxiv.org/schemas/atom"/>{cat_xml}
</entry>""")
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<feed xmlns="http://www.w3.org/2005/Atom" '
           'xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/" xmlns:arxiv="http://arxiv.org/schemas/atom">'
           f'<opensearch:totalResults>{len(PAPERS)}</opensearch:totalResults>' + "".join(entries) + "</feed>")
    (HERE / "arxiv.xml").write_text(xml, encoding="utf-8")


S2 = {
    "2610.21001": ("BiFlow-VLA uses flow matching to train a bimanual VLA that improves real-world success by 18 points.", 12, 3, "Conference on Robot Learning"),
    "2610.21002": ("", 0, 0, "arXiv.org"),
    "2610.21003": ("A single-camera teleoperation system enables low-cost data collection for humanoid imitation learning.", 4, 0, "arXiv.org"),
    "2610.21005": ("OpenNav-Bench provides 3,000 language-guided navigation episodes to evaluate foundation-model agents.", 2, 0, ""),
    "2610.21006": ("A teacher-student pipeline transfers agile parkour from simulation to a real quadruped zero-shot.", 6, 1, "arXiv.org"),
    "2610.21007": ("Robot foundation model success rate follows power-law scaling with data and model size.", 21, 5, "arXiv.org"),
    "2610.21009": ("A 4D occupancy world model improves autonomous driving planning.", 3, 0, "IEEE Robotics and Automation Letters"),
    "2606.11001": ("A generalist VLA policy performs long-horizon household tasks across embodiments.", 180, 41, "Robotics: Science and Systems"),
    "2603.09001": ("A faster diffusion sampler enables 100 Hz visuomotor policies on real robots.", 95, 20, "arXiv.org"),
}


def build_s2():
    ids = [p[0] for p in PAPERS]
    data = []
    for pid in ids:
        if pid not in S2:
            data.append(None)
            continue
        tldr, c, ic, venue = S2[pid]
        data.append({"paperId": f"s2-{pid}", "tldr": {"model": "tldr@v2", "text": tldr} if tldr else None,
                     "citationCount": c, "influentialCitationCount": ic, "venue": venue,
                     "externalIds": {"ArXiv": pid}})
    (HERE / "s2_ids.json").write_text(json.dumps(ids), encoding="utf-8")
    (HERE / "s2.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def build_hf():
    rows = [
        ("2610.21001", 214, "https://github.com/example/biflow-vla", 1200, "BiFlow-VLA trains bimanual VLA policies with flow matching."),
        ("2610.21003", 96, "", 0, "Single RGB camera whole-body teleoperation for humanoids."),
        ("2610.21004", 41, "https://github.com/example/tactilediff", 310, "Tactile-conditioned diffusion policy for in-hand reorientation reaching 76% real success."),
        ("2610.21007", 158, "", 0, "Scaling laws for robot foundation models."),
        ("2610.21010", 33, "", 0, ""),
    ]
    data = [{"paper": {"id": pid, "upvotes": up, "githubRepo": gh or None, "githubStars": st, "ai_summary": summ},
             "numComments": 2, "title": pid} for pid, up, gh, st, summ in rows]
    (HERE / "hf.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


LLM = [
    ("2610.21001", "BiFlow-VLA：フローマッチングによる双腕Vision-Language-Actionポリシー",
     "フローマッチングで学習した双腕用VLAにより、実環境タスクの成功率を従来比18ポイント改善した。",
     "双腕操作に対応したVLAは推論速度と成功率の両立が難しい。", "1.2万件の遠隔操作デモでフローマッチング学習したVLAモデル。",
     "7自由度アーム2台・実機10タスクで成功率+18pt、30Hzで動作。", "要旨に記載なし", ["vla", "manipulation"],
     ["双腕", "両腕操作", "フローマッチング", "実機実験", "遠隔操作データ"], ["bimanual manipulation", "flow matching", "VLA"], "yes"),
    ("2610.21002", "接触の多い組立作業のための潜在世界モデル",
     "触覚と視覚の潜在表現を予測する世界モデルで、接触の多い組立を計画し、モデルフリーRL比で2倍のサンプル効率を得た。",
     "接触の多い組立は計画が難しい。", "触覚・視覚の将来潜在を予測する世界モデルをシミュレーションで学習。",
     "シミュレーションでモデルフリーRLの2倍のサンプル効率。", "シミュレーションのみの評価", ["world-model", "tactile"],
     ["世界モデル", "組立", "触覚", "シミュレーション", "計画"], ["latent world model", "contact-rich assembly"], "no"),
    ("2610.21003", "単一RGBカメラによるヒューマノイドの全身遠隔操作",
     "単一カメラで人の全身動作をヒューマノイドに写す低コスト遠隔操作で、模倣学習用データを効率よく集められる。",
     "ヒューマノイドの全身デモ収集は高コスト。", "単一RGBカメラで捉えた全身動作をリターゲットする遠隔操作系。",
     "500件のデモで学習した方策が実機で歩行と箱の操作を実現。", "要旨に記載なし", ["humanoid", "imitation"],
     ["ヒューマノイド", "人型ロボット", "遠隔操作", "全身制御", "模倣学習"], ["humanoid teleoperation", "whole-body"], "yes"),
    ("2610.21004", "TactileDiff：GelSight触覚を用いた手内再配置のための拡散ポリシー",
     "高解像度の触覚画像を条件にした拡散ポリシーで、16自由度ハンドの手内再配置を未知物体で76%成功させた。",
     "器用な手での手内操作は視覚だけでは難しい。", "触覚画像で条件付けた拡散ポリシー。",
     "実機で未知物体20個に対し成功率76%。", "要旨に記載なし", ["dexterous", "tactile"],
     ["器用な手", "手内操作", "触覚", "拡散ポリシー", "多指ハンド"], ["in-hand reorientation", "diffusion policy", "tactile"], "yes"),
    ("2610.21005", "OpenNav-Bench：家庭内の言語誘導ナビゲーションベンチマーク",
     "スキャンした60軒の家で3,000件の言語誘導ナビゲーション課題を提供し、基盤モデル型エージェント12種を評価した。",
     "言語誘導ナビゲーションの共通評価基盤が不足。", "60軒の家庭スキャンから3,000エピソードのベンチマークを構築。",
     "基盤モデル型エージェント12種を比較評価。", "要旨に記載なし", ["navigation", "dataset"],
     ["ナビゲーション", "言語指示", "ベンチマーク", "家庭環境"], ["vision-language navigation", "benchmark"], "unknown"),
    ("2610.21006", "教師・生徒蒸留による四脚パルクールのSim2Real転移",
     "特権情報を使う教師方策を深度入力の生徒方策へ蒸留し、実機の四脚ロボットで0.5mの障害物登りをゼロショットで実現した。",
     "俊敏な四脚動作の実機転移は難しい。", "シミュレーションで教師方策を学習し深度ベースの生徒へ蒸留。",
     "実機で0.5mの障害物を登坂。", "要旨に記載なし", ["legged", "sim2real", "rl"],
     ["四脚", "脚ロボット", "パルクール", "Sim2Real", "強化学習"], ["quadruped parkour", "sim-to-real"], "yes"),
    ("2610.21007", "ロボット基盤モデルのスケーリング則",
     "1,000万〜30億パラメータのロボット基盤モデル40種を学習し、成功率がデータ量とモデル規模にべき乗則で伸びることを示した。",
     "ロボット基盤モデルのスケーリング挙動は未解明。", "100万軌跡で規模の異なる40モデルを学習。",
     "成功率がデータとモデル規模に対しべき乗則に従う。", "要旨に記載なし", ["vla"],
     ["基盤モデル", "スケーリング則", "大規模データ"], ["scaling laws", "robot foundation model"], "unknown"),
    ("2610.21008", "意図予測モデルを用いた安全な人とロボットの受け渡し",
     "視線と手の姿勢から人の意図を予測して動作を調整する受け渡し制御で、24人の実験で受け渡し時間を短縮した。",
     "人への物の受け渡しは安全性と速さの両立が課題。", "視線と手の姿勢から意図を予測し距離を保つ制御器。",
     "24人のユーザ実験で受け渡し時間が短縮。", "要旨に記載なし", ["hri"],
     ["人とロボットの協調", "受け渡し", "安全", "意図推定"], ["human-robot handover", "intent prediction"], "unknown"),
    ("2610.21009", "自動運転のための占有グリッド世界モデル",
     "シーンの変化を予測する4D占有世界モデルにより、nuScenesでの自動運転の計画性能を改善した。",
     "自動運転では将来のシーン予測が計画に重要。", "4D占有グリッドを予測する世界モデル。",
     "nuScenesで計画性能が向上。", "要旨に記載なし", ["driving", "world-model"],
     ["自動運転", "世界モデル", "占有グリッド", "経路計画"], ["occupancy world model", "autonomous driving"], "no"),
    ("2606.11001", "pi-Next：汎用ロボット方策",
     "多様なロボットデータで学習した汎用VLA方策が、複数の実機で長期の家事タスクを実行した。",
     "汎用ロボット方策の実現。", "多様なロボットデータで学習したVLA方策。",
     "複数種類の実機で長期の家事タスクを実行。", "要旨に記載なし", ["vla"],
     ["汎用ロボット", "基盤モデル", "家事", "実機実験"], ["generalist policy", "VLA"], "yes"),
    ("2603.09001", "Diffusion Policy 2：高速で頑健な視覚運動方策学習",
     "拡散型の視覚運動方策を見直した高速サンプラーで、実機上100Hzでの動作と頑健性の向上を両立した。",
     "拡散方策は推論が遅い。", "高速なサンプラーを提案。", "実機で100Hz動作、頑健性も向上。", "要旨に記載なし",
     ["imitation", "manipulation"], ["拡散ポリシー", "模倣学習", "高速推論"], ["diffusion policy", "visuomotor"], "yes"),
    ("2610.21010", "人の動画から学ぶ器用な把持",
     "ネット上の人の動画から手の姿勢をリターゲットして多指ハンドの把持を学習し、未知物体で60%の成功率を得た。",
     "器用な把持のデータ収集は高コスト。", "人の動画の手姿勢をロボットハンドへリターゲット。",
     "実機の多指ハンドで未知物体の把持成功率60%。", "要旨に記載なし", ["dexterous"],
     ["把持", "器用な手", "人の動画", "多指ハンド"], ["dexterous grasping", "human videos"], "yes"),
]


def build_llm():
    papers = []
    for pid, tj, tl, pr, me, re_, li, tags, kja, ken, rr in LLM:
        papers.append({"id": pid, "title_ja": tj, "tldr_ja": tl, "problem": pr, "method": me,
                       "result": re_, "limitation": li, "tags": tags, "keywords_ja": kja,
                       "keywords_en": ken, "real_robot": rr})
    (HERE / "llm.json").write_text(json.dumps({"papers": papers}, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    build_xml(); build_s2(); build_hf(); build_llm()
    print("fixtures written")

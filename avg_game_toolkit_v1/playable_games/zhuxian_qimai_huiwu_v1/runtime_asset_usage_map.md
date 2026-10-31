# 诛仙_v1 运行素材接入清单

- Runtime JSON: `handoff/avg_game_toolkit_v1/playable_games/zhuxian_qimai_huiwu_v1/runtime/runtime_game_package.json`
- Asset root: `handoff/avg_game_toolkit_v1/playable_games/zhuxian_qimai_huiwu_v1/assets/zhuxian_qimai_huiwu_v1`
- Runtime asset entries: 87
- Unique runtime file paths: 52
- Missing runtime files: 0

## 分类总览

| 分类 | 文件夹 | runtime条目数 | 实际文件数 | 用途 |
| --- | --- | ---: | ---: | --- |
| 角色立绘/人设 | `characters/` | 34 | 23 | 角色人设、对话立绘、表情切换；随说话人和剧情节点切换 |
| 场景背景 | `backgrounds/` | 8 | 7 | 主屏幕背景；按节点/场景切换 |
| 道具/特写 | `props/` | 3 | 3 | 佛珠、剑鞘、判磬等特写；当前主链路不强行展示 |
| 关键CG/结局图 | `cgs/` | 11 | 6 | 关键招式、终招、结局画面；作为主屏CG/节点媒体 |
| 视频/视频首帧 | `video/` | 4 | 6 | n01、n03 开场全屏视频；vff 为首帧参考/兜底 |
| UI概念/皮肤参考 | `ui_concepts/` | 27 | 9 | UI皮肤/组件概念参考；runtime 文案由 DOM 渲染，不进剧情主屏 |

## 角色立绘/人设

| asset_id | 类型 | 用途标签 | 文件 | 应用场景 |
| --- | --- | --- | --- | --- |
| `char_judge_elder_authoritative` | image | character_expression | `characters/char_judge_elder_authoritative.png` | 节点立绘层: n34_ending_gate｜结局门:所有选择都落回自身 / 角色表情映射: 执事长老:default；执事长老:authoritative_calm |
| `char_judge_elder_alert` | image | character_expression | `characters/char_judge_elder_warning.png` | 节点立绘层: n01_arrival_pavilion｜上山:四强台前的脚步；n04_judge_rules｜判磬之下:门规宣告；n06_stage_eye｜目光之桥:擂台中央；n08_choice_opening_stance｜起手姿态(CH1) 等 19 处 / 角色表情映射: 执事长老:alert_attention |
| `char_judge_elder_warning` | image | character_expression | `characters/char_judge_elder_warning.png` | 资产库/后续参考；当前主链路不直接展示 |
| `char_lu_xueqi_blade_pause` | image | character_expression | `characters/char_lu_xueqi_blade_pause.png` | 角色表情映射: 陆雪琪:blade_pause |
| `char_lu_xueqi_after_duel_wait` | image | character_expression | `characters/char_lu_xueqi_neutral_serious.png` | 节点立绘层: n03_lu_arrival｜对面台阶:陆雪琪登场；n04_judge_rules｜判磬之下:门规宣告；n06_stage_eye｜目光之桥:擂台中央；n08_choice_opening_stance｜起手姿态(CH1) 等 30 处 / 角色表情映射: 陆雪琪:after_duel_wait |
| `char_lu_xueqi_neutral_serious` | image | character_expression | `characters/char_lu_xueqi_neutral_serious.png` | 角色表情映射: 陆雪琪:default；陆雪琪:neutral_serious |
| `char_lu_xueqi_eye_distant` | image | character_expression | `characters/char_lu_xueqi_probe_eye.png` | 角色表情映射: 陆雪琪:eye_distant |
| `char_lu_xueqi_probe_eye` | image | character_expression | `characters/char_lu_xueqi_probe_eye.png` | 角色表情映射: 陆雪琪:probe_eye |
| `char_lu_xueqi_hurt_acknowledge` | image | character_expression | `characters/char_lu_xueqi_respect_press.png` | 角色表情映射: 陆雪琪:hurt_acknowledgement |
| `char_lu_xueqi_respect_press` | image | character_expression | `characters/char_lu_xueqi_respect_press.png` | 角色表情映射: 陆雪琪:respect_press |
| `char_lu_xueqi_eye_pain_awe` | image | character_expression | `characters/char_lu_xueqi_surprised_subtle.png` | 角色表情映射: 陆雪琪:eye_pain_awe |
| `char_lu_xueqi_surprised_subtle` | image | character_expression | `characters/char_lu_xueqi_surprised_subtle.png` | 角色表情映射: 陆雪琪:surprised_subtle |
| `char_lu_xueqi_passing_farewell` | image | character_expression | `characters/char_lu_xueqi_understanding_close.png` | 角色表情映射: 陆雪琪:passing_farewell |
| `char_lu_xueqi_understanding_close` | image | character_expression | `characters/char_lu_xueqi_understanding_close.png` | 角色表情映射: 陆雪琪:understanding_close |
| `char_song_daren_worried` | image | character_expression | `characters/char_song_daren_worried.png` | 节点立绘层: n01_arrival_pavilion｜上山:四强台前的脚步；n02_sect_box_pressure｜看台:师门的眼光；n21_tian_buyi_reaction｜看台:师父的拂尘紧了一寸；n22_song_daren_optional｜看台呼喊(若出场):师弟,稳! 等 5 处 / 角色表情映射: 宋大仁:default；宋大仁:worried_restrained |
| `char_tian_buyi_holding_in` | image | character_expression | `characters/char_tian_buyi_holding_in.png` | 资产库/后续参考；当前主链路不直接展示 |
| `char_tian_buyi_paternal_concern` | image | character_expression | `characters/char_tian_buyi_paternal_concern.png` | 资产库/后续参考；当前主链路不直接展示 |
| `char_tian_buyi_serious` | image | character_expression | `characters/char_tian_buyi_serious_silent.png` | 节点立绘层: n01_arrival_pavilion｜上山:四强台前的脚步；n02_sect_box_pressure｜看台:师门的眼光；n04_judge_rules｜判磬之下:门规宣告；n06_stage_eye｜目光之桥:擂台中央 等 22 处 / 角色表情映射: 田不易:default |
| `char_tian_buyi_serious_silent` | image | character_expression | `characters/char_tian_buyi_serious_silent.png` | 资产库/后续参考；当前主链路不直接展示 |
| `char_zhang_xiaofan_buddha_reveal` | image | character_expression | `characters/char_zhang_xiaofan_buddha_reveal.png` | 角色表情映射: 张小凡:buddha_reveal |
| `char_zhang_xiaofan_full_reveal` | image | character_expression | `characters/char_zhang_xiaofan_buddha_reveal.png` | 角色表情映射: 张小凡:full_reveal |
| `char_zhang_xiaofan_gaze_truth` | image | character_expression | `characters/char_zhang_xiaofan_gaze_truth.png` | 资产库/后续参考；当前主链路不直接展示 |
| `char_zhang_xiaofan_hurt_endure` | image | character_expression | `characters/char_zhang_xiaofan_hurt_endure.png` | 角色表情映射: 张小凡:hurt_endure |
| `char_zhang_xiaofan_kneel_failure` | image | character_expression | `characters/char_zhang_xiaofan_hurt_endure.png` | 角色表情映射: 张小凡:kneel_failure |
| `char_zhang_xiaofan_yield_blade` | image | character_expression | `characters/char_zhang_xiaofan_hurt_endure.png` | 角色表情映射: 张小凡:yield_blade |
| `char_zhang_xiaofan_inner_strain` | image | character_expression | `characters/char_zhang_xiaofan_inner_strain.png` | 角色表情映射: 张小凡:inner_strain |
| `char_zhang_xiaofan_back_neutral` | image | character_expression | `characters/char_zhang_xiaofan_neutral_tense.png` | 节点立绘层: n01_arrival_pavilion｜上山:四强台前的脚步；n03_lu_arrival｜对面台阶:陆雪琪登场；n04_judge_rules｜判磬之下:门规宣告；n05_hidden_stir｜袖中:佛珠与道息 等 36 处 |
| `char_zhang_xiaofan_neutral_tense` | image | character_expression | `characters/char_zhang_xiaofan_neutral_tense.png` | 节点立绘层: n34_ending_gate｜结局门:所有选择都落回自身 / 角色表情映射: 张小凡:default；张小凡:neutral_tense |
| `char_zhang_xiaofan_sincere_resolve` | image | character_expression | `characters/char_zhang_xiaofan_sincere_resolve.png` | 角色表情映射: 张小凡:sincere_resolve |
| `ref_judge_elder` | image | character_portrait | `characters/ref_judge_elder.png` | 资产库/后续参考；当前主链路不直接展示 |
| `ref_lu_xueqi` | image | character_portrait | `characters/ref_lu_xueqi.png` | 资产库/后续参考；当前主链路不直接展示 |
| `ref_song_daren` | image | character_portrait | `characters/ref_song_daren.png` | 资产库/后续参考；当前主链路不直接展示 |
| `ref_tian_buyi` | image | character_portrait | `characters/ref_tian_buyi.png` | 资产库/后续参考；当前主链路不直接展示 |
| `ref_zhang_xiaofan` | image | character_portrait | `characters/ref_zhang_xiaofan.png` | 资产库/后续参考；当前主链路不直接展示 |

## 场景背景

| asset_id | 类型 | 用途标签 | 文件 | 应用场景 |
| --- | --- | --- | --- | --- |
| `bg_arena_center_facing` | image | background | `backgrounds/bg_arena_center_facing.png` | 资产库/后续参考；当前主链路不直接展示 |
| `bg_dazhu_inner_chamber` | image | background | `backgrounds/bg_dazhu_inner_chamber.png` | 背景: n29_tian_buyi_private｜师门私下:你出事了吗?；n30_choice_disclosure｜对师门坦白(CH7)；n31_disclosure_aftermath｜回声:师父放下,或不放下；e_restrained_secret_kept｜普通结局:克制惜败,守住秘密 |
| `bg_dazhu_inner_chamber_evening` | image | background | `backgrounds/bg_dazhu_inner_chamber_evening.png` | 资产库/后续参考；当前主链路不直接展示 |
| `bg_opposite_stairs_wisp` | image | background | `backgrounds/bg_opposite_stairs_wisp.png` | 背景: n03_lu_arrival｜对面台阶:陆雪琪登场 |
| `bg_outer_court_threshold` | image | background | `backgrounds/bg_outside_arena_dispersing_crowd.png` | 背景: n33_choice_continue｜是否进入下一场(CH8)；n34_ending_gate｜结局门:所有选择都落回自身 |
| `bg_outside_arena_dispersing_crowd` | image | background | `backgrounds/bg_outside_arena_dispersing_crowd.png` | 资产库/后续参考；当前主链路不直接展示 |
| `bg_qingyun_summit_arena_wide` | image | background | `backgrounds/bg_qingyun_summit_arena_wide.png` | 背景: n01_arrival_pavilion｜上山:四强台前的脚步；n04_judge_rules｜判磬之下:门规宣告；n05_hidden_stir｜袖中:佛珠与道息；n06_stage_eye｜目光之桥:擂台中央 等 31 处 |
| `bg_sect_box_dazhu` | image | background | `backgrounds/bg_sect_box_dazhu.png` | 背景: n02_sect_box_pressure｜看台:师门的眼光；n21_tian_buyi_reaction｜看台:师父的拂尘紧了一寸；n22_song_daren_optional｜看台呼喊(若出场):师弟,稳! |

## 道具/特写

| asset_id | 类型 | 用途标签 | 文件 | 应用场景 |
| --- | --- | --- | --- | --- |
| `prop_buddhist_beads_closeup` | image | prop | `props/prop_buddhist_beads_closeup.png` | 资产库/后续参考；当前主链路不直接展示 |
| `prop_judge_bell_closeup` | image | prop | `props/prop_judge_bell_closeup.png` | 资产库/后续参考；当前主链路不直接展示 |
| `prop_qinglian_sword_sheathed` | image | prop | `props/prop_qinglian_sword_sheathed.png` | 资产库/后续参考；当前主链路不直接展示 |

## 关键CG/结局图

| asset_id | 类型 | 用途标签 | 文件 | 应用场景 |
| --- | --- | --- | --- | --- |
| `cg_burst_first_strike` | image | story_still | `cgs/cg_burst_first_strike.png` | 资产库/后续参考；当前主链路不直接展示 |
| `cg_ending_failure_blank_record` | image | story_still | `cgs/cg_ending_failure_blank_record.png` | 资产库/后续参考；当前主链路不直接展示 |
| `cg_ending_failure_pavilion` | image | story_still | `cgs/cg_ending_failure_blank_record.png` | 节点媒体/开场视频/CG: e_failure_lost_self｜失败结局:失控或拒绝认领 |
| `cg_ending_restrained_dusk_distance` | image | story_still | `cgs/cg_ending_restrained_dusk_distance.png` | 资产库/后续参考；当前主链路不直接展示 |
| `cg_ending_restrained_window` | image | story_still | `cgs/cg_ending_restrained_dusk_distance.png` | 节点媒体/开场视频/CG: e_restrained_secret_kept｜普通结局:克制惜败,守住秘密 |
| `cg_ending_true_dawn` | image | story_still | `cgs/cg_ending_true_dawn_double_view.png` | 节点媒体/开场视频/CG: e_true_recognized_self｜真结局:既承认真心,也承担代价 |
| `cg_ending_true_dawn_double_view` | image | story_still | `cgs/cg_ending_true_dawn_double_view.png` | 资产库/后续参考；当前主链路不直接展示 |
| `cg_ending_yield_inner_chamber` | image | story_still | `cgs/cg_ending_yield_inner_chamber.png` | 资产库/后续参考；当前主链路不直接展示 |
| `cg_ending_yield_mountain_path` | image | story_still | `cgs/cg_ending_yield_inner_chamber.png` | 节点媒体/开场视频/CG: e_recognition_through_yield｜普通结局:主动收手,换得一份理解 |
| `cg_ending_exposure_court` | image | story_still | `cgs/cg_final_strike_settle.png` | 节点媒体/开场视频/CG: e_exposure_won_at_cost｜普通结局:强行取胜,代价已落 |
| `cg_final_strike_settle` | image | story_still | `cgs/cg_final_strike_settle.png` | 资产库/后续参考；当前主链路不直接展示 |

## 视频/视频首帧

| asset_id | 类型 | 用途标签 | 文件 | 应用场景 |
| --- | --- | --- | --- | --- |
| `vff_arrival_drum_step` | image | story_still | `video/vff_arrival_drum_step.png` | 资产库/后续参考；当前主链路不直接展示 |
| `vff_lu_arrival_intent` | image | story_still | `video/vff_lu_arrival_intent.png` | 资产库/后续参考；当前主链路不直接展示 |
| `vid_arrival_drum_step` | video | video_clip | `video/vid_arrival_drum_step.mp4` | 节点媒体/开场视频/CG: n01_arrival_pavilion｜上山:四强台前的脚步 |
| `vid_lu_arrival_intent` | video | video_clip | `video/vid_lu_arrival_intent.mp4` | 节点媒体/开场视频/CG: n03_lu_arrival｜对面台阶:陆雪琪登场 |

## UI概念/皮肤参考

| asset_id | 类型 | 用途标签 | 文件 | 应用场景 |
| --- | --- | --- | --- | --- |
| `ui_axis_meter_three_track` | ui | ui_skin | `ui_concepts/ui_axis_meter_three_track.png` | 节点媒体/开场视频/CG: n08_choice_opening_stance｜起手姿态(CH1) |
| `ui_axis_meter_truth_plus` | ui | ui_skin | `ui_concepts/ui_axis_meter_three_track.png` | 节点媒体/开场视频/CG: n09b_sincere_opening｜真诚开局:他持剑半寸抬高 |
| `ui_meter_three_pane_critical` | ui | ui_skin | `ui_concepts/ui_axis_meter_three_track.png` | 节点媒体/开场视频/CG: n19_choice_revealing｜关键招式(CH4) |
| `ui_meter_three_pane_final` | ui | ui_skin | `ui_concepts/ui_axis_meter_three_track.png` | 节点媒体/开场视频/CG: n24_choice_final_strike｜终招姿态(CH5) |
| `ui_choice_panel_critical` | ui | ui_skin | `ui_concepts/ui_choice_panel_pressure_preview.png` | 节点媒体/开场视频/CG: n19_choice_revealing｜关键招式(CH4) |
| `ui_choice_panel_disclosure` | ui | ui_skin | `ui_concepts/ui_choice_panel_pressure_preview.png` | 节点媒体/开场视频/CG: n30_choice_disclosure｜对师门坦白(CH7) |
| `ui_choice_panel_final` | ui | ui_skin | `ui_concepts/ui_choice_panel_pressure_preview.png` | 节点媒体/开场视频/CG: n24_choice_final_strike｜终招姿态(CH5) |
| `ui_choice_panel_pressure_preview` | ui | ui_skin | `ui_concepts/ui_choice_panel_pressure_preview.png` | 节点媒体/开场视频/CG: n08_choice_opening_stance｜起手姿态(CH1) |
| `ui_choice_panel_three_costs` | ui | ui_skin | `ui_concepts/ui_choice_panel_pressure_preview.png` | 节点媒体/开场视频/CG: n15_choice_protection｜护或不护(CH3) |
| `ui_choice_panel_with_costs` | ui | ui_skin | `ui_concepts/ui_choice_panel_pressure_preview.png` | 节点媒体/开场视频/CG: n12_choice_response｜应对剑势(CH2) |
| `ui_choice_panel_endgame` | ui | ui_skin | `ui_concepts/ui_ending_title_card.png` | 节点媒体/开场视频/CG: n33_choice_continue｜是否进入下一场(CH8) |
| `ui_ending_title_card` | ui | ui_skin | `ui_concepts/ui_ending_title_card.png` | 资产库/后续参考；当前主链路不直接展示 |
| `ui_overlay_ending_card_exposure` | ui | ui_skin | `ui_concepts/ui_ending_title_card.png` | 节点媒体/开场视频/CG: e_exposure_won_at_cost｜普通结局:强行取胜,代价已落 |
| `ui_overlay_ending_card_failure` | ui | ui_skin | `ui_concepts/ui_ending_title_card.png` | 节点媒体/开场视频/CG: e_failure_lost_self｜失败结局:失控或拒绝认领 |
| `ui_overlay_ending_card_restrained` | ui | ui_skin | `ui_concepts/ui_ending_title_card.png` | 节点媒体/开场视频/CG: e_restrained_secret_kept｜普通结局:克制惜败,守住秘密 |
| `ui_overlay_ending_card_true` | ui | ui_skin | `ui_concepts/ui_ending_title_card.png` | 节点媒体/开场视频/CG: e_true_recognized_self｜真结局:既承认真心,也承担代价 |
| `ui_overlay_ending_card_yield` | ui | ui_skin | `ui_concepts/ui_ending_title_card.png` | 节点媒体/开场视频/CG: e_recognition_through_yield｜普通结局:主动收手,换得一份理解 |
| `ui_exposure_meter_concept` | ui | ui_skin | `ui_concepts/ui_exposure_meter_concept.png` | 资产库/后续参考；当前主链路不直接展示 |
| `ui_meter_exposure_preview` | ui | ui_skin | `ui_concepts/ui_exposure_meter_concept.png` | 节点媒体/开场视频/CG: n15_choice_protection｜护或不护(CH3) |
| `ui_lu_attitude_meter_concept` | ui | ui_skin | `ui_concepts/ui_lu_attitude_meter_concept.png` | 资产库/后续参考；当前主链路不直接展示 |
| `ui_choice_panel_post_duel` | ui | ui_skin | `ui_concepts/ui_midsummary_card.png` | 节点媒体/开场视频/CG: n28_choice_post_duel_response｜回应陆雪琪(CH6) |
| `ui_midsummary_card` | ui | ui_skin | `ui_concepts/ui_midsummary_card.png` | 资产库/后续参考；当前主链路不直接展示 |
| `ui_overlay_chapter_card` | ui | ui_skin | `ui_concepts/ui_overlay_chapter_card.png` | 资产库/后续参考；当前主链路不直接展示 |
| `ui_overlay_chapter_card_act1` | ui | ui_skin | `ui_concepts/ui_overlay_chapter_card.png` | 节点媒体/开场视频/CG: n01_arrival_pavilion｜上山:四强台前的脚步 |
| `ui_overlay_rule_card` | ui | ui_skin | `ui_concepts/ui_overlay_rule_card.png` | 节点媒体/开场视频/CG: n04_judge_rules｜判磬之下:门规宣告 |
| `ui_meter_state_three_pane` | ui | ui_skin | `ui_concepts/ui_state_summary_card.png` | 节点媒体/开场视频/CG: n12_choice_response｜应对剑势(CH2) |
| `ui_state_summary_card` | ui | ui_skin | `ui_concepts/ui_state_summary_card.png` | 节点媒体/开场视频/CG: n10_first_clash_merge｜第一回合:三股开局合于一刻；n34_ending_gate｜结局门:所有选择都落回自身 |

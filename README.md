# nonebot-plugin-repeater-count

✨ 群聊复读行为统计插件 ✨

## 功能说明

### 自动记录规则
- 当**连续两条相同消息**且由**不同用户**发送时，视为有效复读行为
- 自动记录以下三类数据：
  - 📊 复读用户（触发复读行为的用户）
  - 😇 被复读用户（原始消息发送者）
  - 🔠 复读词汇（被复读的原始消息内容）

### 统计时段说明
支持四种时间维度统计，基于自然时间划分：

| 时段类型  | 说明      | 重置时间         |
|-------|---------|--------------|
| total | 总统计（默认） | 永不重置         |
| year  | 年度统计    | 每年1月1日 00:00 |
| month | 月度统计    | 每月1日 00:00   |
| day   | 每日统计    | 每天 00:00     |

### 可用命令列表
| 命令格式            | 功能说明       | 示例            |
|-----------------|------------|---------------|
| `/复读排行 [时段类型]`  | 查看复读用户排行榜  | `/复读排行 month` |
| `/被复读排行 [时段类型]` | 查看被复读用户排行榜 | `/受害者排行 day`  |
| `/复读词排行 [时段类型]` | 查看复读热词排行榜  | `/复读词排行 year` |

### 排行榜特性
- 默认显示**TOP 10**排名
- 相同次数按字母/数字顺序排列
- 数据实时更新，即时反映最新复读情况

## 安装方式

使用 nb-cli 安装：
```bash
nb plugin install nonebot-plugin-repeater-count
```
或使用 pip 安装：
```bash
pip install nonebot-plugin-repeater-count
```
## 使用示例
### 基础使用
```plaintext
/复读排行
👉 显示总排行榜（total）

/复读统计 month
👉 显示本月复读排行

/被复读排行 day
👉 显示今日被复读用户排行

/复读词排行
👉 显示历史所有复读热词
```
### 典型输出格式

[total] 时段的复读机排行榜：
1. 用户A - 42次
2. 用户B - 38次
3. 用户C - 35次

...

## 注意事项
### ⚠️ 重要说明

需要 OneBot V11 适配器支持

仅统计群聊消息，私聊消息不会触发记录

数据存储在 data/repeater_data.json 文件，重启后数据保留

每日0点自动重置日统计，每月/年同理

消息对比为纯文本比对（忽略图片/表情等富媒体内容）

### 🔒 数据存储方式：

使用 JSON 格式本地存储

自动创建 data 目录存放数据文件

采用 UTF-8 编码确保兼容性

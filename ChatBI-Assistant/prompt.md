
1、帮我编写Python，使用tushare，获取贵州茅台、五粮液、广发证券、中芯国际的历史价格，从2020-01-01到今天，环境变量 TUSHARE_TOKEN已经设置，按照时间从小到大进行排序，保存到一个worksheet，保存到 .xlsx中

2、帮我生成对应的SQL建表语句，然后将数据放到 sqlite 数据库中

3、基于刚才创建好的  sqlite数据库，改写成 股票查询助手，这里使用qwen-agent，参考@assistant_ticket_bot-3.py，编写新的 .py

4、在 ExcSQLTool中的call中自动对提取到的数据df进行了可视化（柱状图）
但如果len(df)较大，需要自动采用折线图进行呈现。且横坐标可以做一些筛选，比如选取10个点
改写的代码，写入到 assistant_stock_bot-2.py

5、当结果只有一行数据的时候，不需要进行统计信息，也不需要可视化图表

6、在 ExcSQLTool中的call中的md目前会提取df的前10行，这里可以改成提取df的前5行+df的后5行，同时给出这个df的描述统计，方便让AI看到更综合的信息

7、我想使用ARIMA，对未来N天的股票价格进行预测，编写工具 arima_stock
传入股票的ts_code，以及预测的天数 n，这里ts_code是必填
预测的时候需要先从本地sqlite中获取该股票的数据，获取截止到今天的前一年的历史价格，然后使用ARIMA进行建模（5,1,5），并对未来n天的价格进行预测
在@assistant_stock_bot-2.py 的基础上进行编写，写入到 assistant_stock_bot-3.py
8、在ARIMA返回结果中，增加图表的可视化，将过去一段时间的价格，以及未来N天的价格 放到折线图中

9、我想对某支股票的异常点进行检测，使用boll布林带，用使用20日周期+2σ进行检测，默认检测过去1年的超买和超卖日期。
也可以让用户自定义范围，检测这段时间的超买和超卖点
编写 boll_detection工具。这里应该也要先从本地sqlite中获取该股票的数据，然后再进行检测。
在@assistant_stock_bot-3.py 的基础上进行编写，写入到 assistant_stock_bot-4.py

10、CASE-ChatBI助手-20260420 中的 assistant_stock_bot-4.py 我想使用nanobot框架，你可以看下 D:\推荐系统\知乎\新课程\37-项目实战：ChatBI开发实战\CASE-nanobot使用，帮我规划下，另外前端有什么建议，可以放到新项目 CASE-ChatBI助手-nanobot-cli 中 （可以先不考虑前端）

11、帮我搭建 gradio界面，参考 CASE-ChatBI助手 中的 stock_analysis_assistant-6.py 这里使用的 qwen-agent中的 WebUI，我把 qwen-agent 开源项目也copy过来了，你可以参考下

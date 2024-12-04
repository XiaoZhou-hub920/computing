from flask import Flask, render_template, request, redirect, url_for
import pyodbc
from azure.identity import DefaultAzureCredential  # Azure AD 身份验证
from azure.storage.blob import BlobServiceClient
import matplotlib.pyplot as plt
# 配置 Flask 应用
app = Flask(__name__)

# SQL 数据库连接信息
server = 'projectname.database.windows.net'  # 替换为你的 SQL Server 名称
database = 'project'  # 替换为你的数据库名称
driver = '{ODBC Driver 18 for SQL Server}'  # 驱动程序名称
# Azure Blob Storage 配置信息
blob_connection_string = "DefaultEndpointsProtocol=https;AccountName=jieguo;AccountKey=jXVH9heX0HM6A4qVNe1YVxmjT+fyufDtraIuCv1VUa0p0Qa98d3wGhgVw0jpasxGiNcZ+fxcUTmu+ASt8LtbeQ==;EndpointSuffix=core.windows.net"
container_name = "vote-results"

# 通过 Azure AD 集成身份验证连接到 SQL 数据库
def get_db_connection():
    # 获取 Azure AD 凭证
    credential = DefaultAzureCredential()
    
    # 获取连接字符串，使用 Azure AD 身份验证
    connection_string = f'DRIVER={driver};SERVER={server};PORT=1433;DATABASE={database};Authentication=ActiveDirectoryInteractive'
    
    # 使用 Azure AD 身份验证连接
    conn = pyodbc.connect(connection_string)
    return conn

# 上传图表到 Azure Blob Storage
def upload_chart_to_blob(chart_path):
    blob_service_client = BlobServiceClient.from_connection_string(blob_connection_string)
    blob_client = blob_service_client.get_blob_client(container=container_name, blob="results_chart.png")
    with open(chart_path, "rb") as data:
        blob_client.upload_blob(data, overwrite=True)
    return f"https://jieguo.vote-results.blob.core.windows.net/{container_name}/results_chart.png"

# 首页：展示投票选项
@app.route('/')
def index():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM VotingOptions')
    options = cursor.fetchall()
    conn.close()
    return render_template('index.html', options=options)

# 提交投票
@app.route('/vote', methods=['POST'])
def vote():
    option_id = request.form['option']
    user_id = request.form['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()

    # 更新投票数
    cursor.execute('UPDATE VotingOptions SET Votes = Votes + 1 WHERE OptionID = ?', (option_id,))
    conn.commit()

    # 插入投票记录
    cursor.execute('INSERT INTO VotingRecords (UserID, OptionID) VALUES (?, ?)', (user_id, option_id))
    conn.commit()
    conn.close()

    return redirect(url_for('results'))

# 查看投票结果
@app.route('/results')
def results():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM VotingOptions')
    options = cursor.fetchall()
    conn.close()

    # 生成图表
    chart_path = "static/results_chart.png"
    names = [option.OptionName for option in options]
    votes = [option.Votes for option in options]
    plt.bar(names, votes, color='skyblue')
    plt.xlabel('Football Stars')
    plt.ylabel('Votes')
    plt.title('Voting Results')
    plt.savefig(chart_path)

    # 上传到 Blob Storage
    chart_url = upload_chart_to_blob(chart_path)

    return render_template('results.html', options=options, chart_url=chart_url)

if __name__ == '__main__':
    app.run(debug=True)
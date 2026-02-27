import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

def init_knowledge_graph():
    # Load environment variables
    # Try backend/.env first (if run from project root) then direct .env
    if os.path.exists("backend/.env"):
        load_dotenv("backend/.env")
    else:
        load_dotenv()
        
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("Error: DATABASE_URL not found in environment or .env file.")
        return

    print(f"Connecting to: {db_url}")
    engine = create_engine(db_url)

    sql_statements = [
        # 1. Enable extension
        "CREATE EXTENSION IF NOT EXISTS ltree;",
        
        # 2. Create table
        """
        CREATE TABLE IF NOT EXISTS knowledge_nodes (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            path ltree NOT NULL
        );
        """,
        
        # 3. Create indexes
        "CREATE INDEX IF NOT EXISTS path_gist_idx ON knowledge_nodes USING GIST (path);",
        "CREATE INDEX IF NOT EXISTS path_idx ON knowledge_nodes USING BTREE (path);",
        
        # 4. Clear old data
        "TRUNCATE TABLE knowledge_nodes RESTART IDENTITY;",
        
        # 5. Insert data
        """
        INSERT INTO knowledge_nodes (name, path) VALUES 
        ('高中数学(沪教版)', 'SH_MATH'),
        ('集合与逻辑', 'SH_MATH.01'),
        ('集合的概念与运算', 'SH_MATH.01.01'),
        ('命题、定理与逻辑联结词', 'SH_MATH.01.02'),
        ('充分条件与必要条件', 'SH_MATH.01.03'),
        ('不等式', 'SH_MATH.02'),
        ('不等式的性质与解法', 'SH_MATH.02.01'),
        ('基本不等式及其应用', 'SH_MATH.02.02'),
        ('函数', 'SH_MATH.03'),
        ('函数的概念、定义域与值域', 'SH_MATH.03.01'),
        ('函数的性质', 'SH_MATH.03.02'),
        ('幂、指、对函数', 'SH_MATH.03.03'),
        ('函数的零点与方程的解', 'SH_MATH.03.04'),
        ('三角函数', 'SH_MATH.04'),
        ('三角函数的概念', 'SH_MATH.04.01'),
        ('同角三角函数关系与诱导公式', 'SH_MATH.04.02'),
        ('三角恒等变换', 'SH_MATH.04.03'),
        ('三角函数的图像 with 性质', 'SH_MATH.04.04'),
        ('解三角形', 'SH_MATH.04.05'),
        ('数列与数学归纳法', 'SH_MATH.05'),
        ('数列的概念与通项公式', 'SH_MATH.05.01'),
        ('等差数列与等比数列', 'SH_MATH.05.02'),
        ('数列的求和方法', 'SH_MATH.05.03'),
        ('数列的极限与数学归纳法', 'SH_MATH.05.04'),
        ('平面向量与复数', 'SH_MATH.06'),
        ('平面向量的线性运算与坐标表示', 'SH_MATH.06.01'),
        ('平面向量的数量积及其应用', 'SH_MATH.06.02'),
        ('复数的概念与代数运算', 'SH_MATH.06.03'),
        ('解析几何', 'SH_MATH.07'),
        ('直线与方程', 'SH_MATH.07.01'),
        ('圆的方程与位置关系', 'SH_MATH.07.02'),
        ('椭圆的方程与性质', 'SH_MATH.07.03'),
        ('双曲线与抛物线的方程与性质', 'SH_MATH.07.04'),
        ('圆锥曲线综合问题', 'SH_MATH.07.05'),
        ('立体几何', 'SH_MATH.08'),
        ('空间几何体的表面积与体积', 'SH_MATH.08.01'),
        ('点、线、面的位置关系', 'SH_MATH.08.02'),
        ('空间向量的应用', 'SH_MATH.08.03'),
        ('概率与统计', 'SH_MATH.09'),
        ('排列、组合与二项式定理', 'SH_MATH.09.01'),
        ('古典概型与条件概率', 'SH_MATH.09.02'),
        ('随机变量及其分布', 'SH_MATH.09.03'),
        ('统计基础与正态分布', 'SH_MATH.09.04'),
        ('导数及其应用', 'SH_MATH.10'),
        ('导数的概念与运算', 'SH_MATH.10.01'),
        ('导数与函数单调性及极值', 'SH_MATH.10.02'),
        ('导数综合问题', 'SH_MATH.10.03');
        """
    ]

    with engine.connect() as conn:
        # PostgreSQL doesn't allow CREATE EXTENSION inside a transaction block easily sometimes
        # but SQLAlchemy usually handles this. Setting autocommit if needed.
        conn.execution_options(isolation_level="AUTOCOMMIT")
        
        for i, stmt in enumerate(sql_statements, 1):
            try:
                print(f"Executing step {i}...")
                conn.execute(text(stmt))
            except Exception as e:
                print(f"Error in step {i}: {e}")
                # We might want to continue or abort. Let's abort for safety if it's a structural error.
                if i < 5: 
                    return

    print("\nKnowledge graph initialization completed successfully!")

if __name__ == "__main__":
    init_knowledge_graph()

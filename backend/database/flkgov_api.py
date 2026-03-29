from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Optional

app = FastAPI(title="flkgov API")

DB_CONFIG = {
    'host': '192.168.1.40',
    'port': 5432,
    'database': 'flkgov_db',
    'user': 'flkgov_user',
    'password': '1421nbnb'
}

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


class RegulationSearchRequest(BaseModel):
    keyword: str


class ArticleSearchRequest(BaseModel):
    regulation_id: int


@app.get("/flkgov/regulations")
def search_regulations(keyword: Optional[str] = None, limit: Optional[str] = None) -> List[dict]:
    """
    获取法规列表，支持关键词搜索
    """
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if keyword:
                if limit:
                    query = """
                        SELECT * FROM flkgov_regulations 
                        WHERE title LIKE %s
                        ORDER BY id
                        LIMIT %s
                    """
                    pattern = f"%{keyword}%"
                    cur.execute(query, (pattern, int(limit)))
                else:
                    query = """
                        SELECT * FROM flkgov_regulations 
                        WHERE title LIKE %s
                        ORDER BY id
                    """
                    pattern = f"%{keyword}%"
                    cur.execute(query, (pattern,))
            else:
                if limit:
                    query = "SELECT * FROM flkgov_regulations ORDER BY id LIMIT %s"
                    cur.execute(query, (int(limit),))
                else:
                    query = "SELECT * FROM flkgov_regulations ORDER BY id"
                    cur.execute(query)
            
            results = cur.fetchall()
            return [dict(row) for row in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.get("/flkgov/regulations/{regulation_id}")
def get_regulation(regulation_id: str) -> dict:
    """
    根据ID获取单个法规详情
    """
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = "SELECT * FROM flkgov_regulations WHERE id = %s"
            cur.execute(query, (int(regulation_id),))
            result = cur.fetchone()
            if not result:
                raise HTTPException(status_code=404, detail="法规不存在")
            return dict(result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.get("/flkgov/articles")
def search_articles(regulation_id: Optional[str] = None, limit: Optional[str] = None) -> List[dict]:
    """
    获取条款列表，支持按regulation_id筛选
    """
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if regulation_id:
                if limit:
                    query = """
                        SELECT * FROM flkgov_articles 
                        WHERE regulation_id = %s
                        ORDER BY id
                        LIMIT %s
                    """
                    cur.execute(query, (int(regulation_id), int(limit)))
                else:
                    query = """
                        SELECT * FROM flkgov_articles 
                        WHERE regulation_id = %s
                        ORDER BY id
                    """
                    cur.execute(query, (int(regulation_id),))
            else:
                if limit:
                    query = "SELECT * FROM flkgov_articles ORDER BY id LIMIT %s"
                    cur.execute(query, (int(limit),))
                else:
                    query = "SELECT * FROM flkgov_articles ORDER BY id"
                    cur.execute(query)
            
            results = cur.fetchall()
            return [dict(row) for row in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

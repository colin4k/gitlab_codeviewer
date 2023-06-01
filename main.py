import uvicorn
from fastapi import FastAPI

web_port = 14441

def create_app() -> FastAPI: 
    app = FastAPI()
    register_rotuer(app)
    return app


def register_rotuer(app: FastAPI) -> None:
    #注册路由
    from api import routers
    app.include_router(routers)
    
app = create_app()

if __name__ == "__main__":
     # manage对应manage.py的文件名，app则对应app这个实例
    print(f'接口服务已启动，监听端口:{web_port}')
    uvicorn.run("main:app", host="0.0.0.0", port=web_port,reload=True)
    
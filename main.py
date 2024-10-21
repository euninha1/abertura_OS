from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import cx_Oracle
from fastapi.staticfiles import StaticFiles
import uvicorn
from fastapi import Request

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oracle_user = 'abertura_os'
oracle_password = 'Dti*dec*++os@'
oracle_dsn = '10.222.0.17:1521/medbd.set.edu.br'

class OrdemServico(BaseModel):
    nr_seq_localizacao: int
    nr_seq_equipamento: int
    ds_dano_breve: str
    ds_dano: str
    cd_pessoa_solicitante: int

class User(BaseModel):
    username: str

class OrdemdeServico(BaseModel):
    ds_dano_breve: str
    ds_solucao: str

class SessionData:
    ds_dano_breve = None

ds_dano_breve_global = None
usuario_global = None

@app.get("/obter_usuarios")
async def obter_usuarios():
    try:
        connection = cx_Oracle.connect(oracle_user, oracle_password, oracle_dsn)
        cursor = connection.cursor()
        query = """
        select a.cd_pessoa_fisica,
        a.ds_usuario
        from   tasy.dc_usuario_solicitante_app_v a
        ORDER BY 2
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()
        connection.close()
        
        usuarios = [{"cd_pessoa_fisica": row[0], "ds_usuario": row[1]} for row in rows]
        return JSONResponse(content=usuarios)
    except cx_Oracle.Error as error:
        print(f"Erro ao conectar ao Oracle: {str(error)}")
        raise HTTPException(status_code=500, detail="Erro ao conectar ao Oracle")

@app.get("/obter_setores")
async def obter_setores():
    try:
        connection = cx_Oracle.connect(oracle_user, oracle_password, oracle_dsn)
        cursor = connection.cursor()
        query = """
       select a.nr_sequencia,
       a.ds_localizacao
        from   tasy.dc_localizacao_os_app_v a
        ORDER BY 2
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()
        connection.close()
        
        setores = [{"cd_setor": row[0], "ds_localizacao": row[1]} for row in rows]
        return JSONResponse(content=setores)
    except cx_Oracle.Error as error:
        print(f"Erro ao conectar ao Oracle: {str(error)}")
        raise HTTPException(status_code=500, detail="Erro ao conectar ao Oracle")

@app.post("/validate_user")
async def validate_user(user: User):
    global usuario_global
    try:
        connection = cx_Oracle.connect(oracle_user, oracle_password, oracle_dsn)
        cursor = connection.cursor()
        query = """
        SELECT a.nm_usuario, a.cd_setor_atendimento 
        FROM tasy.usuario a 
        WHERE a.nm_usuario = :username AND a.cd_setor_atendimento = 127 and ie_situacao = 'A'
        """
        cursor.execute(query, username=user.username)
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        if result is not None:
            usuario_global = user.username  
            return {"message": "Usuário validado com sucesso!"}
        else:
            raise HTTPException(status_code=401, detail="Usuário inválido")
    except cx_Oracle.Error as error:
        print(f"Erro cx_Oracle ao conectar ou executar consulta: {error}")
        raise HTTPException(status_code=500, detail="Erro interno ao conectar ou consultar o Oracle")


@app.post("/criar_ordem_servico")
async def criar_ordem_servico(ordem: OrdemServico):
    try:
        connection = cx_Oracle.connect(oracle_user, oracle_password, oracle_dsn)
        cursor = connection.cursor()
        query = """
        INSERT INTO tasy.man_ordem_servico (
            nr_sequencia,
            nr_seq_localizacao,
            nr_seq_equipamento,
            cd_pessoa_solicitante,
            dt_ordem_servico,
            ie_prioridade,
            ie_parado,
            ds_dano_breve,
            dt_atualizacao,
            nm_usuario,
            ds_dano,
            dt_inicio_previsto,
            dt_inicio_real,
            ie_tipo_ordem,
            ie_status_ordem,
            nr_grupo_planej,
            nr_grupo_trabalho,
            nr_seq_estagio,
            ie_classificacao,
            ds_contato_solicitante
        )
        VALUES (
            tasy.man_ordem_servico_seq.nextval,
            :nr_seq_localizacao,
            :nr_seq_equipamento,
            :cd_pessoa_solicitante,
            sysdate,
            'A',
            'N',
            :ds_dano_breve,
            sysdate,
            :username,
            :ds_dano,
            sysdate,
            sysdate,
            1,
            1,
            21,
            21,
            14,
            'D',
            '2391'
        )
        """
        cursor.execute(
            query,
            nr_seq_localizacao=ordem.nr_seq_localizacao,
            nr_seq_equipamento=ordem.nr_seq_equipamento,
            ds_dano_breve=ordem.ds_dano_breve,
            ds_dano=ordem.ds_dano,
            cd_pessoa_solicitante=ordem.cd_pessoa_solicitante,
            username=oracle_user
        )
        # Atualiza a variável global com a descrição do chamado
        global ds_dano_breve_global
        ds_dano_breve_global = ordem.ds_dano_breve
        connection.commit()
        cursor.close()
        connection.close()
        return {"message": "Ordem de serviço criada com sucesso!"}
    except cx_Oracle.Error as error:
        print(f"Erro ao conectar ao Oracle: {str(error)}")
        raise HTTPException(status_code=500, detail="Erro ao conectar ao Oracle")

@app.post("/armazenar_ds_dano_breve")
async def armazenar_ds_dano_breve(ds_dano_breve: str):
    global ds_dano_breve_global
    ds_dano_breve_global = ds_dano_breve
    return {"message": "ds_dano_breve armazenado com sucesso!"}

@app.post("/verificar_e_atualizar")
async def verificar_e_atualizar(ordem: OrdemdeServico, request: Request):
    global ds_dano_breve_global
    global usuario_global
    try:
        print("Dentro de verificar_e_atualizar")
        print(f"Solicitação recebida em {request.url}")

        
        body = await request.json()  
        usuario = body.get("usuario")  
        
        if usuario_global is None:
            print("Erro: Usuário não logado.")
            raise HTTPException(status_code=400, detail="Usuário não logado.")

        print(f'Usuário logado: {usuario}')

        if ds_dano_breve_global is None:
            print("Erro: Descrição do chamado não armazenada.")
            raise HTTPException(status_code=400, detail="Descrição do chamado não armazenada. Use /armazenar_ds_dano_breve primeiro.")

        connection = cx_Oracle.connect(oracle_user, oracle_password, oracle_dsn)
        cursor = connection.cursor()

        print(f"Antes de executar a consulta com ds_dano_breve_global: {ds_dano_breve_global}")
        cursor.execute(
            "SELECT ds_dano_breve, ie_status_ordem FROM tasy.man_ordem_servico WHERE ds_dano_breve = :ds_dano_breve AND ROWNUM = 1 FOR UPDATE WAIT 600",
            ds_dano_breve=ds_dano_breve_global,
        )
        result = cursor.fetchone()
        print(f"Resultado da consulta: {result}")

        if result:
            ds_dano_breve, ie_status_ordem = result
            if ie_status_ordem == 3:
                print(f"Chamado já encerrado: {ds_dano_breve}")
                raise HTTPException(status_code=400, detail="Chamado já encerrado")

            print(f"Atualizando chamado {ds_dano_breve} com a solução: {ordem.ds_solucao}")
            cursor.execute(
                """UPDATE tasy.man_ordem_servico
                SET 
                    ie_status_ordem = 3,
                    ds_solucao = :ds_solucao,
                    dt_fim_real = sysdate,
                    nm_usuario_exec = :username
                WHERE ds_dano_breve = :ds_dano_breve""",
                ds_dano_breve=ds_dano_breve,
                ds_solucao=ordem.ds_solucao,
                username=usuario_global 
            )
            connection.commit()
            cursor.close()
            connection.close()
            print("Chamado encerrado com sucesso!")
            return {"message": "Chamado encerrado com sucesso!"}
        else:
            print("Erro: Chamado não encontrado ou já encerrado.")
            raise HTTPException(status_code=400, detail="Chamado não encontrado ou já encerrado")
    
    except cx_Oracle.Error as error:
        print(f"Erro ao conectar ao Oracle: {str(error)}")
        raise HTTPException(status_code=500, detail="Erro ao conectar ao Oracle")
    
    except Exception as e:
        print(f"Erro na função verificar_e_atualizar: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="10.222.1.25", port=5501)

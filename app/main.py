import json
import base64
from aiohttp import web
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from models import Role
from models import Session, engine, Base
from models import Users, Advertisements, UserAdvertisements
from bcrypt import hashpw, gensalt, checkpw

import asyncio
def hash_password(password: str):
    password = password.encode()
    password = hashpw(password, salt=gensalt())
    password = password.decode()
    return password


def check_password(password: str, hashed_password: str):
    return checkpw(password.encode(), hashed_password=hashed_password.encode())

async def orm_context(app):
    print("START")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()
    print('SHUT DOWN')

@web.middleware
async def session_middleware(request: web.Request, handler):
    async with Session() as session:
        request['session'] = session
        response = await handler(request)
        return response

@web.middleware
async def auth_middleware(request, handler):
    method = request.method
    auth_methods = ['POST','PATCH','DELETE']
    response = {}
    view_class = request.match_info.handler
    
    if method == 'POST' and view_class == UserView:
            response = await handler(request)
            return response
    
    if method in auth_methods:
        
        if not 'Authorization' in request.headers:
            raise web.HTTPNonAuthoritativeInformation(
                text=json.dumps({'error': 'no authorization data'}),
                content_type='application/json'
            )

        auth_header = request.headers['Authorization']

        try:
            encoded_credentials = auth_header[6:].strip()
            decoded_credentials = base64.b64decode(encoded_credentials).decode('utf-8')
            decoded_credentials = decoded_credentials.split(':')
            name = decoded_credentials[0]
            password = decoded_credentials[1]
        except:
            raise web.HTTPNonAuthoritativeInformation(
                text=json.dumps({'error': 'bad authorization'}),
                content_type='application/json'
            )
        user = await get_user_by_name(name,request['session'])

        if check_password(password, user.password):
            request['user'] = user
            response = await handler(request)
            return response
        else:
            raise web.HTTPNotAcceptable(
                text=json.dumps({'error': 'authorization denial'}),
                content_type='application/json'
            )
        
    response = await handler(request)
    return response
            
        
        

async def get_user_by_name(name,session):
    result = await session.execute(select(Users).where(Users.username == name))
    user = result.scalars().first()
    if user is None:
        raise web.HTTPNotFound(
            text=json.dumps({'error': 'user not found'}),
            content_type='application/json'
        )
    return user

    
async def get_user(user_id, session):
    user = await session.get(Users, user_id)
    if user is None:
        raise web.HTTPNotFound(
            text=json.dumps({'httperror': 'user not found'}),
            content_type='application/json'
        )
    return user

async def get_advertisement(advertisement_id, session):
    advertisement = await session.get(Advertisements, advertisement_id)
    if advertisement is None:
        raise web.HTTPNotFound(
            text=json.dumps({'httperror':'advertisement not faund'}),
            content_type= 'appliction/json'
            )
    return advertisement

class UserView(web.View):

    @property
    def session(self):
        self.request.match_info.handler.__class__
        return self.request['session']
    
        
    @property
    def user_id(self):
        return int(self.request.match_info['user_id'])

    async def get (self):
        user = await get_user(self.user_id,self.session)
        respons = web.json_response({'id':user.id,'name':user.username,
                                     'email':user.email,'role':str(user.role),
                                     'create_time':str(user.create_time)})
        return respons
    
    async def post(self):

        json_data = await self.request.json()
        copy_json_data = await self.request.json()
        keys = ['password','username','email']
        if not set(keys).issubset(set(list(json_data.keys()))):
            
            raise web.HTTPBadRequest(
                text= json.dumps({'parametrsERROR':'Bad parametrs'}),
                content_type='appliction/json')

        json_data['password'] = hash_password(json_data['password'])
        user = Users(**json_data)
        self.session.add(user)
        try:
            await self.session.commit()
        except:
            raise web.HTTPBadRequest(
            text=json.dumps({'error': 'username is busy'}),
            content_type='application/json'
            )
        return web.json_response({'id':user.id})
        

    async def patch(self):
        user = await get_user(self.user_id,self.session)
        json_data = await self.request.json()
        if 'password' in json_data:
            json_data['password'] = hash_password(json_data['password'])
        for field, value in json_data.items():
            setattr(user, field, value)
        self.session.add(user)
        await self.session.commit()
        return web.json_response({'id': user.id})

    async def delete(self):
        user = await get_user(self.user_id, self.session)
        await self.session.delete(user)
        await self.session.commit()
        return web.json_response({'id': user.id})



class AdvertisementView(web.View):

    @property
    def user(self):
        return self.request['user']
    
    @property
    def session(self):
        return self.request['session']
    
    @property
    def advertisement_title(self):
        return self.request.match_info['title']
    
    @property
    def advertisement_id(self):
        return int(self.request.match_info['id'])


    async def get (self):
        
        results = await self.session.execute(
            select(Advertisements).join(UserAdvertisements).join(Users).where(
                Advertisements.title == self.advertisement_title
                    ).options(joinedload(Advertisements.user))
        )

        respons = []
        for result in results.unique().scalars():
            advertisement = result
            user, = advertisement.user
            respons.append({
            'advertisement_id':advertisement.id,
            'title':advertisement.title,
            'description':advertisement.description,
            
            'creator':
                {
                'id':user.id,
                'name':user.username,
                },
            })

        return web.json_response(respons)
    
    async def post(self):
        user = self.user
        json_data = await self.request.json()
        advertisement = Advertisements(**json_data)
        self.session.add(advertisement)
        await self.session.commit()
        user_advertisements = UserAdvertisements(
            user_id = user.id,
            advertisement_id = advertisement.id
        )
        self.session.add(user_advertisements)
        await self.session.commit()
        return web.json_response(
        {
            'advertisement_id':advertisement.id,
            'title':advertisement.title,
            'description':advertisement.description,
            
            'creator':
        {
            'id':user.id,
            'name':user.username,
        },
        })
       
    async def patch(self):
        json_data = await self.request.json()
        session = self.session
        user = self.user
        advertisement = await get_advertisement(self.advertisement_id,session)
        user_advertisement = await session.execute(
            select(UserAdvertisements)\
                .where(
                    UserAdvertisements.advertisement_id == advertisement.id
                ))
        
        user_advertisement = user_advertisement.scalars().first()
        if user_advertisement.user_id != user.id and user.role == Role.user:
            raise web.HTTPUnauthorized(
                text=json.dump({'httperror':'access denied'}),
                content_type='application/json')
        
        for field, value in json_data.items():
            setattr(advertisement, field, value)
        
        session.add (advertisement)
        await session.commit()
        return web.json_response(
        {
            'advertisement_id':advertisement.id,
            'title':advertisement.title,
            'description':advertisement.description,
            
            'creator':
        {
            'id':user.id,
            'name':user.username,
        },
        })
       
    async def delete(self):
        session = self.session
        user = self.user
        advertisement = await get_advertisement(self.advertisement_id,session)

        user_advertisement = await session.execute(
            select(UserAdvertisements)\
                .where(
                    UserAdvertisements.advertisement_id == advertisement.id
                ))
        
        user_advertisement = user_advertisement.scalars().first()
        if user_advertisement.user_id != user.id and user.role == Role.user:
            raise web.HTTPUnauthorized(
                text=json.dumps({'httperror':'access denied'}),
                content_type='application/json')

        await session.delete(advertisement)
        await session.commit()


       

def get_app():
    app = web.Application()
    app.cleanup_ctx.append(orm_context)
    app.middlewares.append(session_middleware)
    app.middlewares.append(auth_middleware)
    app.add_routes(
        [
            web.get("/user/{user_id:\d+}", UserView),
            web.patch("/user/{user_id:\d+}", UserView),
            web.delete("/user/{user_id:\d+}", UserView),
            web.post("/user/", UserView),
            web.get("/advertisement/{title}",AdvertisementView),
            web.patch("/advertisement/{id:\d+}", AdvertisementView),
            web.delete("/advertisement/{id:\d+}", AdvertisementView),
            web.post("/advertisement/", AdvertisementView),
        ]
    )

    return app

if __name__ == '__main__':
    app = get_app()
    web.run_app(app)
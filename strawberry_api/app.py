from fastapi import FastAPI, Response
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

import strawberry
from strawberry.fastapi import GraphQLRouter

from sqlalchemy import select, delete

from typing import List, Optional

import models

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_credentials=True,
        allow_methods='POST, GET, DELETE, OPTIONS',
        allow_headers=['*']
    )
]

app = FastAPI(middleware=middleware)

@strawberry.type
class Pet: 
    id: strawberry.ID
    name: str
    birthday: str
    domain: str
    gender: str
    breed: str = None
    weight: float = None
    microchip: int
    photo: str = None
    adoption: str = None
    adoption_info: str = None


    @classmethod
    def marshal(cls, model: models.Pet) -> "Pet":
        return cls(
            id=strawberry.ID(str(model.id)),
            name=model.name,
            birthday=model.birthday,
            domain=model.domain,
            gender=model.gender,
            breed=model.breed,
            weight=model.weight,
            microchip=model.microchip,
            photo=model.photo,
            adoption=model.adoption,
            adoption_info=model.adoption_info
        )

@strawberry.input
class PetDataInput: 
    name: str = None
    birthday: str = None
    domain: str = None
    gender: str = None
    breed: str = None
    weight: float = None
    microchip: int = None
    photo: str = None
    adoption: str = None
    adoption_info: str = None

@strawberry.input
class PetQueryInput:
    termo: Optional[str] = strawberry.UNSET

@strawberry.type
class PetExists:
    message: str = "Pet de mesmo microchip já inserido na base"

@strawberry.type
class PetNotFound:
    message: str = "Não foi possível encontrar o pet"

@strawberry.type
class PetRemoveMessage:
    message: str = "Pet removido com sucesso"

PetResponse = strawberry.union("PetResponse", (Pet, PetExists, PetNotFound, PetRemoveMessage))

@strawberry.type
class Query:

    @strawberry.field
    async def all_pets(self) -> List[Pet]:
        async with models.get_session() as session:
            sql = select(models.Pet).order_by(models.Pet.name)
            db_pets = (await session.execute(sql)).scalars().unique().all()

        return [Pet.marshal(pet) for pet in db_pets]

            
    @strawberry.field
    async def search_pet(self, query_input: Optional[PetQueryInput] = None) -> List[Pet]:
        async with models.get_session() as session:
            if query_input:
                sql = select(models.Pet) \
                        .filter(models.Pet.name.ilike(f"%{query_input.termo}%")).\
                            order_by(models.Pet.name)
            else:
                sql = select(models.Pet).order_by(models.Pet.name)

            db_pets = (await session.execute(sql)).scalars().unique().all()

        return [Pet.marshal(pet) for pet in db_pets]

@strawberry.type
class Mutation:

    @strawberry.field
    async def add_pet(self, name: str, birthday: str, domain: str, gender: str, 
                      breed: str, weight: float, microchip: int, photo: str, adoption: str, adoption_info: str) -> PetResponse: 
        async with models.get_session() as session:

            sql = select(models.Pet).\
                filter(models.Pet.microchip == microchip)
            db_pet_exists = (await session.execute(sql)).scalars().unique().all()

            if db_pet_exists:
                return PetExists()

            db_pet = models.Pet(name=name, birthday=birthday, domain=domain, gender=gender, 
                                breed=breed, weight=weight, microchip=microchip, photo=photo, 
                                adoption=adoption, adoption_info=adoption_info)
            session.add(db_pet)
            await session.commit()

        return Pet.marshal(db_pet)

    @strawberry.field
    async def edit_pet(self, id: int, edits: PetDataInput) -> PetResponse: 
        async with models.get_session() as session:

            sql = select(models.Pet).\
                filter(models.Pet.id == id)
            db_pet_exists = (await session.execute(sql)).scalars().first()

            if not db_pet_exists:
                return PetNotFound()
            
            if edits.name != None: db_pet_exists.name = edits.name
            if edits.birthday != None: db_pet_exists.birthday = edits.birthday
            if edits.domain != None: db_pet_exists.domain = edits.domain
            if edits.gender != None: db_pet_exists.gender = edits.gender
            if edits.breed != None: db_pet_exists.breed = edits.breed
            if edits.weight != None: db_pet_exists.weight = edits.weight
            if edits.microchip != None: db_pet_exists.microchip = edits.microchip
            if edits.photo != None: db_pet_exists.photo = edits.photo
            if edits.adoption != None: db_pet_exists.adoption = edits.adoption
            if edits.adoption_info != None: db_pet_exists.adoption_info = edits.adoption_info
            
            await session.commit()

        return Pet.marshal(db_pet_exists)

    @strawberry.field
    async def remove_pet(self, id: int) -> PetResponse: 
        async with models.get_session() as session:
            try:
                sql = select(models.Pet).filter(models.Pet.id == id)
                result = await session.execute(sql)
                db_pet_exists = result.scalars().first()

                if not db_pet_exists:
                    return PetNotFound()

                # Deleta o pet
                await session.delete(db_pet_exists)
                await session.commit()

                return PetRemoveMessage()

            except Exception as e:
                await session.rollback()
                # Log do erro para debugging (opcional)
                print(f"Erro ao remover pet: {e}")
                raise e

schema = strawberry.Schema(query=Query, mutation=Mutation)

graphql_app = GraphQLRouter(schema)

app.include_router(graphql_app, prefix="/graphql")
import json

from marshmallow import ValidationError
from nameko.exceptions import BadRequest
from nameko.rpc import rpc, RpcProxy
from nameko_sqlalchemy import Database
from werkzeug.wrappers import Response

from user_manager.entrypoints import http
from user_manager.exceptions import (
    GroupNotFoundError,
    UserNotFoundError,
    AreaNotFoundError,
)
from user_manager.models import DeclarativeBase, User, Group, ProfilePicture, Area
from user_manager.schema import CreateUserSchema, CreateGroupSchema


class UserManager:
    name = "user_manager"

    db = Database(DeclarativeBase)

    @rpc
    def get_user(self, user_id):
        with self.db.get_session() as sess:
            user = sess.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"User id {user_id} doesn't exists")
            return user.as_dict()


class UserManagerService:
    name = "user_manager_http"

    db = Database(DeclarativeBase)

    rekognizer = RpcProxy("rekognizer")

    @http("POST", "/users", expected_exceptions=(ValidationError, BadRequest))
    def create_user(self, request):
        schema = CreateUserSchema(strict=True)

        try:
            user_data = schema.loads(request.get_data(as_text=True)).data
        except ValueError as exc:
            raise BadRequest("Invalid json: {}".format(exc))

        user_result = self._create_user(
            user_data["first_name"],
            user_data["last_name"],
            user_data["profile_pictures"],
            user_data["group_ids"],
            user_data["expiration_date"],
        )

        return Response(json.dumps(user_result), mimetype="application/json")

    def _create_user(
        self, first_name, last_name, profile_pictures, group_ids, expiration_date
    ):
        user = User(
            first_name=first_name, last_name=last_name, expiration_date=expiration_date
        )
        with self.db.get_session() as sess:
            for group_id in group_ids:
                group = sess.query(Group).filter(Group.id == group_id).first()
                if not group:
                    raise GroupNotFoundError(f"Group id {group_id} doesn't exists")
                user.groups.append(group)
            sess.add(user)
            sess.flush()
            for i in profile_pictures:
                profile_picture = ProfilePicture(picture_url=i, user_id=user.id)
                sess.add(profile_picture)

        # TODO: change to event pubsub
        self.rekognizer.enroll_user(user_id=user.id, image_urls=profile_pictures)

        return user.as_dict()

    @http("GET", "/users")
    def get_users(self, request):
        users = self.db.session.query(User).all()
        users = [user.as_dict() for user in users]

        return Response(json.dumps(users), mimetype="application/json")

    @http("GET", "/users/<int:user_id>")
    def get_user(self, request, user_id):
        user = self.db.session.query(User).filter(User.id == user_id).first()
        if not user:
            raise UserNotFoundError(f"User {user_id} doesn't exist")

        return Response(json.dumps(user.as_dict()), mimetype="application/json")

    @http("GET", "/groups")
    def get_groups(self, request):
        groups = self.db.session.query(Group).all()
        groups = [group.as_dict() for group in groups]

        return Response(json.dumps(groups), mimetype="application/json")

    @http("GET", "/groups/<int:group_id>")
    def get_group(self, request, group_id):
        group = self.db.session.query(Group).filter(Group.id == group_id).first()
        if not group:
            raise GroupNotFoundError(f"Group {group_id} doesn't exist")

        return Response(json.dumps(group.as_dict()), mimetype="application/json")

    @http("GET", "/areas")
    def get_areas(self, request):
        areas = self.db.session.query(Area).all()
        areas = [area.as_dict() for area in areas]

        return Response(json.dumps(areas), mimetype="application/json")

    @http("POST", "/groups", expected_exceptions=(ValidationError, BadRequest))
    def create_group(self, request):
        schema = CreateGroupSchema(strict=True)

        try:
            group_data = schema.loads(request.get_data(as_text=True)).data
        except ValueError as exc:
            raise BadRequest("Invalid json: {}".format(exc))

        group_result = self._create_group(group_data["name"], group_data["area_ids"])

        return Response(json.dumps(group_result), mimetype="application/json")

    def _create_group(self, name, area_ids):
        group = Group(name=name)
        with self.db.get_session() as sess:
            for area_id in area_ids:
                area = sess.query(Area).filter(Area.id == area_id).first()
                if not area:
                    raise AreaNotFoundError(f"Area id {area_id} doesn't exists")
                group.areas.append(area)
            sess.add(group)

        return group.as_dict()

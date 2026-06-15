from ninja import ModelSchema

from app.organization.models import Organizations


class OrganizationSchema(ModelSchema):
    class Meta:
        model = Organizations
        fields = "__all__"


class OrganizationCreateSchema(ModelSchema):
    class Meta:
        model = Organizations
        fields = ["name", "slug", "industry"]


class OrganizationUpdateSchema(ModelSchema):
    class Meta:
        model = Organizations
        fields = ["name", "slug", "industry", "is_active"]

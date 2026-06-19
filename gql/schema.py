"""Strawberry schema assembly.

This module is the single entry point imported by the Django URL config.
It combines Query + Mutation into the final executable schema.
"""

from __future__ import annotations

import strawberry
from strawberry.django.views import GraphQLView

from .mutations import Mutation
from .queries import Query

schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
)

# GraphQLView instance used in wellbeing/urls.py
# GraphiQL is enabled by default in DEBUG mode; Strawberry honours the
# Django DEBUG setting automatically when graphiql=True.
graphql_view = GraphQLView.as_view(schema=schema)

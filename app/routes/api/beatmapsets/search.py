
from flask import Blueprint, Response, request
from pydantic import ValidationError
from flask_pydantic import validate

from app.common.database.repositories import beatmapsets
from app.models import SearchRequest, BeatmapsetModel

router = Blueprint('search', __name__)

@router.get('/search')
@validate()
def search_api():
    try:
        query = SearchRequest.model_validate(request.args.to_dict())
    except ValidationError as e:
        return Response(
            response=e.json(),
            status=400,
            mimetype='application/json'
        )

    results = beatmapsets.search_extended(
        query.query,
        query.genre,
        query.language,
        query.played,
        None, # TODO: user_id
        query.mode,
        query.order,
        query.category,
        query.sort,
        query.storyboard,
        query.video,
        query.offset,
        query.limit
    )

    return [
        BeatmapsetModel.model_validate(beatmapset, from_attributes=True) \
                       .model_dump()
        for beatmapset in results
    ]

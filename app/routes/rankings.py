
from app.common.database.repositories import users, stats, histories
from app.common.constants import GameMode
from app.common.cache import leaderboards
from app.common.database import DBUser

from flask import Blueprint, abort, request

import utils

router = Blueprint('rankings', __name__)

@router.get('/<mode>/<order_type>')
def rankings(mode: str, order_type: str):
    if (mode := GameMode.from_alias(mode)) is None:
        return abort(404)

    if order_type not in ('performance', 'rscore', 'tscore', 'ppv1', 'country'):
        return abort(404)

    page = max(1, min(10000, request.args.get('page', default=1, type=int)))
    items_per_page = 49

    # Any two letter country code
    country = request.args.get('country', default=None, type=str)

    if order_type != 'country':
        leaderboard = leaderboards.top_players(
            mode.value,
            offset=(page - 1) * items_per_page,
            range=items_per_page,
            type=order_type,
            country=country.lower()
                if country else None
        )

        # Fetch all users from leaderboard
        users_db = users.fetch_many(
            tuple(user[0] for user in leaderboard), DBUser.stats
        )

        # Sort users based on redis leaderboard
        sorted_users = [
            next(filter(lambda user: id == user.id, users_db))
            for id, score in leaderboard
            if score > 0
        ]

        for index, user in enumerate(sorted_users):
            user.stats.sort(key=lambda x: x.mode)

            # Check if rank in redis has changed
            if (index + 1) != user.stats[mode].rank:
                user.stats[mode].rank = index + 1

                stats.update(
                    user.id,
                    mode,
                    {'rank': user.stats[mode].rank}
                )

                histories.update_rank(user.stats[mode], user.country)
                users.fetch_many.cache_clear()

        player_count = leaderboards.player_count(mode.value, order_type)
        total_pages = max(1, min(10000, round(player_count / items_per_page)))

        # Get min/max pages to display for pagination
        max_page_display = max(page, min(total_pages, page + 8))
        min_page_display = max(1, min(total_pages, max_page_display - 9))

        # Fetch top countries for country selection
        top_countries = leaderboards.top_countries(mode)

        return utils.render_template(
            'rankings.html',
            css='rankings.css',
            mode=mode,
            page=page,
            country=country,
            order_type=order_type,
            total_pages=total_pages,
            leaderboard=sorted_users,
            top_countries=top_countries,
            max_page_display=max_page_display,
            min_page_display=min_page_display,
            order_name={
                'rscore': 'Ranked Score',
                'tscore': 'Total Score',
                'performance': 'Performance',
                'ppv1': 'PPv1'
            }[order_type.lower()]
        )

    leaderboard = leaderboards.top_countries(mode)
    leaderboard = leaderboard[(page - 1)*items_per_page:(page - 1)*items_per_page + items_per_page]

    country_count = len(leaderboard)
    total_pages = max(1, min(10000, round(country_count / items_per_page)))

    # Get min/max pages to display for pagination
    max_page_display = max(page, min(total_pages, page + 8))
    min_page_display = max(1, min(total_pages, max_page_display - 9))

    return utils.render_template(
        'country.html',
        css='country.css',
        mode=mode,
        page=page,
        total_pages=total_pages,
        leaderboard=leaderboard,
        max_page_display=max_page_display,
        min_page_display=min_page_display,
    )


from flask import render_template as _render_template

from app.common.database.repositories import stats, histories, scores
from app.common.helpers import performance
from app.common.cache import leaderboards
from app.common.database import DBUser
from app.common import constants

import config
import app

def render_template(name: str, **kwargs) -> str:
    """This will automatically fetch all the required data for bancho-stats"""
    kwargs.update(
        total_scores=int(app.session.redis.get('bancho:totalscores') or 0),
        online_users=int(app.session.redis.get('bancho:users') or 0),
        total_users=int(app.session.redis.get('bancho:totalusers') or 0),
        constants=constants,
        config=config,
    )

    return _render_template(
        name,
        **kwargs
    )

def sync_ranks(user: DBUser) -> None:
    """Sync cached rank with database"""
    try:
        app.session.logger.debug(f'[{user.name}] Trying to update rank from cache...')

        for user_stats in user.stats:
            if user_stats.playcount <= 0:
                continue

            global_rank = leaderboards.global_rank(user.id, user_stats.mode)

            if user_stats.rank != global_rank:
                # Database rank desynced from redis
                stats.update(
                    user.id,
                    user_stats.mode,
                    {
                        'rank': global_rank
                    }
                )

                # Update rank history
                histories.update_rank(user_stats, user.country)

                app.session.logger.debug(
                    f'[{user.name}] Updated rank from {user_stats.rank} to {global_rank}'
                )
    except Exception as e:
        app.session.logging.error(
            f'[{user.name}] Failed to update user rank: {e}',
            exc_info=e
        )

def update_ppv1(user: DBUser):
    """Update ppv1 calculations for a player"""
    try:
        app.session.logger.debug(f'[{user.name}] Trying to update ppv1 calculations...')

        for user_stats in user.stats:
            if user_stats.playcount <= 0:
                continue

            best_scores = scores.fetch_best(user.id, user_stats.mode, not config.APPROVED_MAP_REWARDS)
            user_stats.ppv1 = performance.calculate_weighted_ppv1(best_scores)

            stats.update(
                user.id,
                user_stats.mode,
                {
                    'ppv1': user_stats.ppv1
                }
            )

            leaderboards.update(
                user_stats,
                user.country
            )

            histories.update_rank(
                user_stats,
                user.country
            )
    except Exception as e:
        app.session.logging.error(
            f'[{user.name}] Failed to update ppv1 calculations: {e}',
            exc_info=e
        )

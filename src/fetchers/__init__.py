"""Conget fetchers module.

This module exports all available fetchers for programmatic access.
"""

from src.fetchers.default import DefaultFetcher
from src.fetchers.github_repo import GitHubRepoFetcher
from src.fetchers.hh_vacancy import HHVacancyFetcher
from src.fetchers.hh_employer import HHEmployerFetcher

__all__ = [
    "DefaultFetcher",
    "GitHubRepoFetcher",
    "HHVacancyFetcher",
    "HHEmployerFetcher",
]

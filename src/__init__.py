"""Conget - Simple CLI library for fetching web content with plugin architecture."""

__version__ = "0.1.0"

# Library API
from src.conget import Conget

# Core interfaces
from src.core.interfaces import BaseFetcher

# All fetchers
from src.fetchers import (
    DefaultFetcher,
    GitHubRepoFetcher,
    HHVacancyFetcher,
    HHEmployerFetcher,
)

__all__ = [
    "Conget",
    "BaseFetcher",
    "DefaultFetcher",
    "GitHubRepoFetcher",
    "HHVacancyFetcher",
    "HHEmployerFetcher",
]

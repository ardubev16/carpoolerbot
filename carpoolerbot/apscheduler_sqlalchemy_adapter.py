"""
PTBSQLAlchemyJobStore adapter for apscheduler.

src: https://github.com/python-telegram-bot/ptbcontrib/tree/main/ptbcontrib/ptb_jobstores
"""

import logging
from typing import Any

from apscheduler.job import Job as APSJob
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from telegram.ext import Application, Job

logger = logging.getLogger(__name__)


class PTBSQLAlchemyJobStore(SQLAlchemyJobStore):
    """Wraps apscheduler.SQLAlchemyJobStore to make :class:`telegram.ext.Job` class storable."""

    def __init__(self, application: Application, **kwargs: Any) -> None:  # noqa: ANN401
        """
        Args:
            application (:class:`telegram.ext.Application`): Application instance
                that will be passed to CallbackContext when recreating jobs.
            **kwargs (:obj:`dict`): Arbitrary keyword Arguments to be passed to
                the SQLAlchemyJobStore constructor.

        """  # noqa: D205
        if kwargs.get("url", "").startswith("sqlite:///"):
            logger.warning(
                "Use of SQLite db is not supported  due to "
                "multi-threading limitations of SQLite databases "
                "You can still try to use it, but it will likely "
                "behave differently from what you expect.",
            )

        self.application = application
        super().__init__(**kwargs)

    @staticmethod
    def _prepare_job(job: APSJob) -> APSJob:
        """
        Erase all unpickable data from telegram.ext.Job.

        Args:
            job (:obj:`apscheduler.job`): The job to be processed.

        """
        # make new job which is copy of actual job cause
        # modifying actual job also modifies jobs in threadpool
        # executor which are currently running/going to run, and
        # we'll get incorrect argument instead of CallbackContext.
        prepped_job = APSJob.__new__(APSJob)
        prepped_job.__setstate__(job.__getstate__())
        # Get the tg_job instance in memory
        tg_job = Job.from_aps_job(job)
        # Extract relevant information from the job and
        # store it in the job's args.
        prepped_job.args = (
            tg_job.name,
            tg_job.data,
            tg_job.chat_id,
            tg_job.user_id,
            tg_job.callback,
        )
        return prepped_job

    def _restore_job(self, job: APSJob) -> APSJob:
        """
        Restore all telegram.ext.Job data.

        Args:
            job (:obj:`apscheduler.job`): The job to be processed.

        """
        name, data, chat_id, user_id, callback = job.args
        tg_job = Job(
            callback=callback,
            chat_id=chat_id,
            user_id=user_id,
            name=name,
            data=data,
        )
        job._modify(  # noqa: SLF001
            args=(
                self.application.job_queue,
                tg_job,
            ),
        )
        return job

    def add_job(self, job: APSJob) -> None:
        """
        Add the given job to this store.

        :param Job job: the job to add
        :raises ConflictingIdError: if there is another job in this store with the same ID
        """
        job = self._prepare_job(job)
        super().add_job(job)

    def update_job(self, job: APSJob) -> None:
        """
        Replace the job in the store with the given newer version.

        :param Job job: the job to update
        :raises JobLookupError: if the job does not exist
        """
        job = self._prepare_job(job)
        super().update_job(job)

    def _reconstitute_job(self, job_state: bytes) -> APSJob:
        """
        Is called from apscheduler's internals when loading job.

        Args:
            job_state (:obj:`str`): String containing pickled job state.

        """
        job: APSJob = super()._reconstitute_job(job_state)
        return self._restore_job(job)

"""Store dataset selection shared by project workflow pages."""
from app.repositories.store_dataset_repository import StoreDatasetRepository


class StoreDatasetService:
    def __init__(self, db):
        self.repository = StoreDatasetRepository(db)

    def active_batch(self, project_id):
        return self.repository.active_batch(project_id)

    def candidate_query(self, batch_id):
        return self.repository.candidate_query(batch_id)

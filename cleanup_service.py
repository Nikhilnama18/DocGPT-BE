from apscheduler.schedulers.background import BackgroundScheduler

from document_repository import delete_document_record, list_documents_for_cleanup
from rag_service import delete_document_embeddings
from storage import delete_from_r2, get_object_key_from_storage_url

CLEANUP_BATCH_SIZE = 200
CLEANUP_INTERVAL_HOURS = 3


def cleanup_expired_and_failed_documents() -> dict:
    """
    Removes expired or failed uploads from R2, Qdrant, and Postgres.
    """
    candidates = list_documents_for_cleanup(limit=CLEANUP_BATCH_SIZE)
    summary = {
        "scanned": len(candidates),
        "deleted": 0,
        "failed": 0,
    }

    if not candidates:
        print("Cleanup job found no expired or failed documents.")
        return summary

    for document in candidates:
        document_id = str(document["id"])

        try:
            object_key = get_object_key_from_storage_url(document["storage_url"])
            delete_from_r2(object_key)
            delete_document_embeddings(document_id)
            delete_document_record(document_id)
            summary["deleted"] += 1
            print(f"Cleaned document {document_id} from R2, Qdrant, and Postgres.")
        except Exception as exc:
            summary["failed"] += 1
            print(f"Cleanup failed for document {document_id}: {exc}")

    print(
        "Cleanup job finished. "
        f"Scanned={summary['scanned']}, "
        f"Deleted={summary['deleted']}, "
        f"Failed={summary['failed']}."
    )
    return summary


def start_cleanup_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        cleanup_expired_and_failed_documents,
        trigger="interval",
        hours=CLEANUP_INTERVAL_HOURS,
        id="document_cleanup",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    scheduler.start()
    print(
        "Started cleanup scheduler. "
        f"Job will run every {CLEANUP_INTERVAL_HOURS} hours."
    )
    return scheduler

from repository.user_repository import (
    get_user_by_id,
    get_user_by_username,
    get_user_by_phone,
    create_user,
    update_user,
    delete_user,
)

from repository.contact_repository import (
    get_contact_by_id,
    get_contacts_by_user,
    create_contact,
    update_contact,
    delete_contact,
)

from repository.message_repository import (
    get_message_by_id,
    get_messages_by_task,
    get_messages_by_contact,
    create_message,
    create_messages_bulk,
    count_messages_by_task,
    delete_message,
    get_limit_messages,
    get_message_count,
    get_contact_ids_by_task,
    get_messages_by_contact_ordered,
)

from repository.task_repository import (
    get_tasks,
    get_task,
    create_task,
    delete_task,
    update_task_status,
    update_task_message_count,
    update_task,
)

from repository.extracted_info_repository import (
    delete_by_task,
    create_extracted_info,
    create_extracted_info_batch,
    get_extracted_info_by_task,
    get_messages_for_extraction,
)

from repository.analysis_result_repository import (
    get_result_types_by_task,
    delete_by_task_and_type,
    create_analysis_result,
    get_analysis_results_by_task,
    count_by_task,
    get_messages_for_analysis,
)

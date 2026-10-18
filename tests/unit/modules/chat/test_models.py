import uuid

from app.modules.chat.enums import MessageRole
from app.modules.chat.models import Conversation, Message


def test_conversation_model_attributes() -> None:
    tenant_id = uuid.uuid4()
    conv = Conversation(
        tenant_id=tenant_id,
        title="Inquiry about 3-bed apartment",
        metadata_={"source": "web_widget"},
    )

    assert conv.tenant_id == tenant_id
    assert conv.title == "Inquiry about 3-bed apartment"
    assert conv.metadata_ == {"source": "web_widget"}
    assert Conversation.__tablename__ == "conversations"


def test_message_model_attributes() -> None:
    tenant_id = uuid.uuid4()
    conv_id = uuid.uuid4()
    msg = Message(
        tenant_id=tenant_id,
        conversation_id=conv_id,
        role=MessageRole.USER,
        content="What is the price of unit 4B?",
        token_count=12,
    )

    assert msg.tenant_id == tenant_id
    assert msg.conversation_id == conv_id
    assert msg.role == MessageRole.USER
    assert msg.content == "What is the price of unit 4B?"
    assert msg.token_count == 12
    assert Message.__tablename__ == "messages"


def test_message_roles_values() -> None:
    assert MessageRole.USER.value == "user"
    assert MessageRole.ASSISTANT.value == "assistant"
    assert MessageRole.SYSTEM.value == "system"

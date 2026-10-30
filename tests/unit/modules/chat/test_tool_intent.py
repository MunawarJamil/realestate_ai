import pytest
from app.modules.chat.hitl_graph import classify_visitor_intent

def test_intent_classification_tool_signals():
    # Calculator signals
    assert classify_visitor_intent("Can you calculate mortgage for a 2M villa?") == "tool_action"
    assert classify_visitor_intent("What would be the monthly payment or emi?") == "tool_action"

    # Booking signals
    assert classify_visitor_intent("I would like to book a viewing for Saturday") == "tool_action"
    assert classify_visitor_intent("Can we schedule viewing for tomorrow?") == "tool_action"

    # Smalltalk
    assert classify_visitor_intent("Hello there!") == "smalltalk"
    assert classify_visitor_intent("Thank you very much") == "smalltalk"

    # General RAG inquiry
    assert classify_visitor_intent("Tell me more about luxury villas in Palm Jumeirah") == "property_inquiry"
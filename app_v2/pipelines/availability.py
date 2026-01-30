"""
Availability pipeline for circles.

Handles fetching availability data and processing it for schedule meeting.
"""

import logging
from typing import Dict, Any, List

from bson import ObjectId

from app_v2.dependencies import get_main_db

logger = logging.getLogger(__name__)


async def get_group_availability_for_scheduling(group_id: str) -> Dict[str, Any]:
    """
    Get detailed availability for scheduling a meeting.

    Returns all time slots with counts of who can attend.

    Args:
        group_id: The circle group ID

    Returns:
        {
            "totalMembers": int,
            "members": [str],  # All member names
            "slots": [
                {
                    "day": int,  # 0-6 (Sun-Sat)
                    "hour": int,  # 0-23
                    "availableCount": int,
                    "availableMembers": [str]
                }
            ]
        }
    """
    db = get_main_db()

    # --- MongoDB Calls ---

    # Get group to find members
    groups_collection = db["circlegroups"]
    group = await groups_collection.find_one({"_id": ObjectId(group_id)})

    if not group:
        return {
            "totalMembers": 0,
            "members": [],
            "slots": []
        }

    # Get availability document for this group
    availability_collection = db["useravailabilities"]
    availability_doc = await availability_collection.find_one({"groupId": ObjectId(group_id)})

    # --- Process Data ---

    # Extract member info from group
    raw_members = group.get("members", [])
    member_ids = []
    member_names_map = {}

    for m in raw_members:
        if isinstance(m, dict):
            mid = str(m.get("userId"))
            name = m.get("name", "Member")
        else:
            mid = str(m)
            name = "Member"
        member_ids.append(mid)
        member_names_map[mid] = name

    total_members = len(member_ids)
    all_member_names = list(member_names_map.values())

    # If no availability set, return empty slots
    if not availability_doc:
        return {
            "totalMembers": total_members,
            "members": all_member_names,
            "slots": []
        }

    # Build slot -> available members mapping
    slots_data = _calculate_slot_availability(
        member_availability=availability_doc.get("memberAvailability", []),
        member_ids=member_ids,
        member_names_map=member_names_map
    )

    return {
        "totalMembers": total_members,
        "members": all_member_names,
        "slots": slots_data
    }


def _calculate_slot_availability(
    member_availability: List[Dict],
    member_ids: List[str],
    member_names_map: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Calculate availability per slot.

    Pure logic function - no DB calls.

    Args:
        member_availability: List of member availability records
        member_ids: List of valid member IDs in the group
        member_names_map: Map of member ID to name

    Returns:
        List of slots with availability counts and member names
    """
    # Map: (day, hour) -> list of member names available
    slot_members: Dict[tuple, List[str]] = {}

    for member in member_availability:
        user_id = str(member.get("userId"))

        # Skip if not a current group member
        if user_id not in member_ids:
            continue

        # Get member name (prefer from availability doc, fallback to map)
        member_name = member.get("name") or member_names_map.get(user_id, "Member")
        slots = member.get("slots", [])

        for slot in slots:
            day = slot.get("day")
            hour = slot.get("hour")

            if day is None or hour is None:
                continue

            key = (day, hour)
            if key not in slot_members:
                slot_members[key] = []
            slot_members[key].append(member_name)

    # Convert to list format, sorted by day then hour
    slots_list = []
    for (day, hour), available_members in sorted(slot_members.items()):
        slots_list.append({
            "day": day,
            "hour": hour,
            "availableCount": len(available_members),
            "availableMembers": available_members
        })

    return slots_list

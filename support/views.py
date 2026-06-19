"""Views for the support workflow.

All views require login. Role gating uses ``role_required`` from
``accounts.permissions``.

Role mapping for this project:
  OPERATOR   — frontline staff who log sessions / mood data
  SUPERVISOR — counselor who reviews cases and resolves escalations
  ADMIN      — program manager / dashboard / assignments
"""

from __future__ import annotations

import logging

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import Role
from accounts.permissions import role_required

from .forms import AssignmentForm, MoodScoreForm, SupportSessionForm
from .models import Assignment, AuditEvent, MoodScore, SupportSession
from .permissions import assert_supporter_owns_youth

logger = logging.getLogger("wellbeing.support")
User = get_user_model()


# ---------------------------------------------------------------------------
# Mood log (Operator enters well-being check-in for a student)
# ---------------------------------------------------------------------------
@role_required(Role.OPERATOR, Role.ADMIN)
def mood_log(request):
    form = MoodScoreForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        entry = form.save(commit=False)
        entry.youth = request.user
        entry.save()
        AuditEvent.objects.create(
            actor=request.user,
            youth=request.user,
            action=AuditEvent.Action.MOOD_LOG,
            detail=f"Score {entry.score} logged.",
        )
        messages.success(request, "Well-being score saved.")
        return redirect("support:mood_history")
    return render(request, "support/mood_log.html", {
        "form": form,
        "recent": MoodScore.objects.filter(youth=request.user).order_by("-created_at")[:5],
    })


# ---------------------------------------------------------------------------
# Mood history
# ---------------------------------------------------------------------------
@role_required(Role.OPERATOR, Role.SUPERVISOR, Role.ADMIN)
def mood_history(request):
    history = (
        MoodScore.objects.filter(youth=request.user)
        .order_by("-created_at")[:30]
    )
    return render(request, "support/mood_history.html", {"history": history})


# ---------------------------------------------------------------------------
# Session log (Operator logs a support session for an assigned student)
# ---------------------------------------------------------------------------
@role_required(Role.OPERATOR)
def session_log(request, youth_pk: int):
    assert_supporter_owns_youth(request.user, youth_pk)
    youth = get_object_or_404(User, pk=youth_pk)
    assignment = get_object_or_404(
        Assignment, youth=youth, peer_supporter=request.user, is_active=True
    )
    form = SupportSessionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        session = form.save(commit=False)
        session.assignment = assignment
        session.logged_by = request.user
        session.save()
        AuditEvent.objects.create(
            actor=request.user,
            youth=youth,
            action=AuditEvent.Action.SESSION_LOG,
            detail=f"Session #{session.pk} logged for {youth.get_full_name() or youth.username}.",
        )
        messages.success(request, "Session logged.")
        return redirect("support:youth_detail", youth_pk=youth_pk)
    return render(request, "support/session_log.html",
                  {"form": form, "youth": youth, "assignment": assignment})


# ---------------------------------------------------------------------------
# Youth / student detail
# ---------------------------------------------------------------------------
@role_required(Role.OPERATOR, Role.SUPERVISOR, Role.ADMIN)
def youth_detail(request, youth_pk: int):
    if request.user.is_operator:
        assert_supporter_owns_youth(request.user, youth_pk)
    youth = get_object_or_404(User, pk=youth_pk)
    mood_scores = MoodScore.objects.filter(youth=youth).order_by("-created_at")[:10]
    assignment = (
        Assignment.objects.filter(youth=youth, is_active=True)
        .select_related("peer_supporter", "counselor")
        .first()
    )
    sessions = (
        SupportSession.objects.filter(assignment__youth=youth)
        .select_related("logged_by", "assignment")
        .order_by("-session_date", "-created_at")
        if assignment else SupportSession.objects.none()
    )
    audit_events = (
        AuditEvent.objects.filter(youth=youth)
        .select_related("actor")
        .order_by("-created_at")
    )
    return render(request, "support/youth_detail.html", {
        "youth": youth,
        "mood_scores": mood_scores,
        "assignment": assignment,
        "sessions": sessions,
        "audit_events": audit_events,
    })


# ---------------------------------------------------------------------------
# Escalate session (Operator escalates to Supervisor)
# ---------------------------------------------------------------------------
@role_required(Role.OPERATOR)
def escalate_session(request, session_pk: int):
    if request.method != "POST":
        raise PermissionDenied("POST required.")
    session = get_object_or_404(
        SupportSession.objects.select_related("assignment__youth"),
        pk=session_pk,
    )
    assert_supporter_owns_youth(request.user, session.assignment.youth_id)
    session.escalate(actor=request.user)
    messages.warning(request, "Session escalated to supervisor.")
    return redirect("support:youth_detail", youth_pk=session.assignment.youth_id)


# ---------------------------------------------------------------------------
# Counselor / Supervisor queue
# ---------------------------------------------------------------------------
@role_required(Role.SUPERVISOR, Role.ADMIN)
def counselor_queue(request):
    pending = (
        SupportSession.objects.filter(
            escalation_status=SupportSession.EscalationStatus.PENDING,
        )
        .select_related(
            "assignment__youth", "assignment__peer_supporter",
            "logged_by", "escalated_by",
        )
        .order_by("-escalated_at")
    )
    return render(request, "support/counselor_queue.html", {"pending_sessions": pending})


# ---------------------------------------------------------------------------
# Resolve session (Supervisor marks escalation resolved)
# ---------------------------------------------------------------------------
@role_required(Role.SUPERVISOR, Role.ADMIN)
def resolve_session(request, session_pk: int):
    if request.method != "POST":
        raise PermissionDenied("POST required.")
    session = get_object_or_404(SupportSession, pk=session_pk)
    session.escalation_status = SupportSession.EscalationStatus.RESOLVED
    session.save(update_fields=["escalation_status", "updated_at"])
    AuditEvent.objects.create(
        actor=request.user,
        youth=session.assignment.youth,
        action=AuditEvent.Action.SESSION_LOG,
        detail=f"Session #{session.pk} escalation resolved by {request.user.username}.",
    )
    messages.success(request, "Session marked as resolved.")
    return redirect("support:counselor_queue")


# ---------------------------------------------------------------------------
# Supervisor dashboard
# ---------------------------------------------------------------------------
@role_required(Role.SUPERVISOR, Role.ADMIN)
def supervisor_dashboard(request):
    security_events = (
        AuditEvent.objects.filter(
            action__in=[
                AuditEvent.Action.ACCESS_DENIED,
                AuditEvent.Action.SUPERVISOR_ALERT,
            ]
        )
        .select_related("actor", "youth")
        .order_by("-created_at")[:20]
    )
    pending_count = SupportSession.objects.filter(
        escalation_status=SupportSession.EscalationStatus.PENDING
    ).count()
    active_assignments = Assignment.objects.filter(is_active=True).count()
    return render(request, "support/supervisor_dashboard.html", {
        "security_events": security_events,
        "pending_count": pending_count,
        "active_assignments": active_assignments,
    })


# ---------------------------------------------------------------------------
# RAG assistant (Operator queries WHO/UNICEF guidelines)
# ---------------------------------------------------------------------------
@role_required(Role.OPERATOR)
def rag_assistant(request):
    result = None
    query = ""
    if request.method == "POST":
        query = request.POST.get("query", "").strip()
        if query:
            from .rag.retriever import retrieve
            result = retrieve(query, top_k=2)
    return render(request, "support/rag_assistant.html",
                  {"result": result, "query": query})


# ---------------------------------------------------------------------------
# Assignment list (Admin creates/views assignments)
# ---------------------------------------------------------------------------
@role_required(Role.ADMIN)
def assignment_list(request):
    form = AssignmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        assignment = form.save()
        AuditEvent.objects.create(
            actor=request.user,
            youth=assignment.youth,
            action=AuditEvent.Action.ASSIGNMENT,
            detail=(
                f"{assignment.youth.get_full_name() or assignment.youth.username} "
                f"assigned to operator "
                f"{assignment.peer_supporter.get_full_name() or assignment.peer_supporter.username}."
            ),
        )
        messages.success(request, "Assignment created.")
        return redirect("support:assignment_list")
    assignments = (
        Assignment.objects.select_related("youth", "peer_supporter", "counselor")
        .order_by("-created_at")
    )
    return render(request, "support/assignment_list.html",
                  {"assignments": assignments, "form": form})

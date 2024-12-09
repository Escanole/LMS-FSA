from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Max, Count, F
from .models import Chat, User, GroupChat
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse
from module_group.models import ModuleGroup
from datetime import datetime


def send_message_form(request):
    if request.method == "POST":
        recipient_username = request.POST.get('recipient')
        message_text = request.POST.get('message')
        sender_username = request.POST.get('sender')  # Assume sender is passed from the form
        recipient = get_object_or_404(User, username=recipient_username)
        sender = get_object_or_404(User, username=sender_username)
        if recipient and sender and message_text:
            Chat.objects.create(sender=sender, receiver=recipient, message=message_text)
            return redirect('chat:chat_view', username=recipient_username)  # Corrected redirect
    users = User.objects.all()
    context = {
        'users': users
    }
    return render(request, 'chat/send_message_form.html', context)

def create_group_chat_view(request):
    if request.method == "POST":
        group_name = request.POST.get('group_name')  # Get group name from the form
        member_usernames = request.POST.getlist('members')  # List of selected usernames

        if group_name and member_usernames:
            # Create the group
            group = GroupChat.objects.create(name=group_name, created_by=request.user)

            # Add the selected members to the group
            for username in member_usernames:
                user = get_object_or_404(User, username=username)
                group.members.add(user)

            # Ensure the creator is also added to the group
            group.members.add(request.user)

            return redirect('chat:chat_view', group_id=group.id)

    # Get all users except the current user
    users = User.objects.exclude(id=request.user.id)

    return render(request, 'chat/create_group_chat.html', {'users': users})

@login_required
def add_member_to_group_view(request, group_id):
    group = get_object_or_404(GroupChat, id=group_id)
    current_user = request.user

    # Ensure the current user is part of the group (either the creator or a member)
    if current_user not in group.members.all() and group.created_by != current_user:
        return redirect('some_error_page')  # Unauthorized access

    if request.method == "POST":
        member_usernames = request.POST.getlist('members')  # List of selected usernames

        # Add the selected members to the group
        for username in member_usernames:
            user = get_object_or_404(User, username=username)
            if user not in group.members.all():  # Avoid adding the same user again
                group.members.add(user)

        return redirect('chat:chat_view', group_id=group.id)

    # Get all users except those who are already in the group
    users = User.objects.exclude(id__in=group.members.all().values_list('id', flat=True))

    return render(request, 'chat/add_member_to_group.html', {'group': group, 'users': users})

@login_required
def remove_member_from_group_view(request, group_id):
    group = get_object_or_404(GroupChat, id=group_id)
    current_user = request.user

    # Ensure the current user is the creator of the group (only the creator can remove members)
    if group.created_by != current_user:
        return redirect('some_error_page')  # Unauthorized access

    if request.method == "POST":
        member_username = request.POST.get('member')  # Username of the member to remove
        member = get_object_or_404(User, username=member_username)

        if member != group.created_by:  # Prevent creator from removing themselves
            group.members.remove(member)

        return redirect('chat:chat_view', group_id=group.id)

    # Get all members of the group except the group creator
    members = group.members.exclude(id=group.created_by.id)

    return render(request, 'chat/remove_member_from_group.html', {'group': group, 'members': members})

@login_required
def edit_message_view(request, message_id):
    message = get_object_or_404(Chat, id=message_id)

    # Ensure the user is the sender of the message
    if message.sender != request.user:
        return redirect('some_error_page')  # Unauthorized access

    if request.method == "POST":
        new_message_text = request.POST.get('message', '').strip()
        if new_message_text:
            message.message = new_message_text
            message.edited_at = timezone.now()  # Set edited timestamp
            message.save()

            # Redirect back to the relevant group chat or direct chat
            if message.group:
                return redirect('chat:chat_view', group_id=message.group.id)
            else:
                return redirect('chat:chat_view', username=message.receiver.username)  # Changed here

    return render(request, 'chat/edit_message.html', {'message': message})

@login_required
def delete_message_view(request, message_id):
    message = get_object_or_404(Chat, id=message_id)

    # Ensure the user is the sender of the message
    if message.sender != request.user:
        return redirect('some_error_page')  # Unauthorized access

    if request.method == "POST":
        message.delete()
        # Redirect back to the relevant group chat or direct chat
        if message.group:
            return redirect('chat:chat_view', group_id=message.group.id)
        else:
            return redirect('chat:chat_view', username=message.receiver.username)  # Changed here

    return render(request, 'chat/delete_message.html', {'message': message})

@login_required
def chat_view(request, username=None, group_id=None):
    current_user = request.user
    users = User.objects.exclude(id=current_user.id)
    group_chats = current_user.group_members.all()
    module_groups = ModuleGroup.objects.all()
    search_query = request.GET.get('search', '')

    # Get unread messages count and preview
    unread_count = Chat.objects.filter(
        receiver=current_user,
        is_read=False
    ).count()

    message_preview = (
        Chat.objects.filter(receiver=current_user)
        .values('sender__username')
        .annotate(
            message_content=Max('message'),
            time_sent=Max('timestamp'),
            is_read=Max('is_read')
        )
        .order_by('-time_sent')[:5]
    )

    if username:
        other_user = get_object_or_404(User, username=username)
        
        # Mark messages as read
        Chat.objects.filter(
            sender=other_user,
            receiver=current_user,
            is_read=False
        ).update(is_read=True)

        # Filter messages between users and apply search if query exists
        messages = Chat.objects.filter(
            (Q(sender=current_user) & Q(receiver=other_user)) |
            (Q(sender=other_user) & Q(receiver=current_user))
        )
        
        if search_query:
            messages = messages.filter(message__icontains=search_query)
        
        messages = messages.order_by('timestamp')

        context = {
            'other_user': other_user,
            'messages': messages,
            'users': users,
            'group_chats': group_chats,
            'user': current_user,
            'module_groups': module_groups,
            'unread_count': unread_count,
            'message_preview': message_preview,
            'search_query': search_query
        }
    else:
        context = {
            'users': users,
            'group_chats': group_chats,
            'user': current_user,
            'module_groups': module_groups,
            'unread_count': unread_count,
            'message_preview': message_preview,
            'search_query': search_query
        }

    return render(request, 'chat/chat_view.html', context)

@login_required
def message_report_view(request):
    current_user = request.user

    report_data = (
        Chat.objects.filter(receiver=current_user)
        .values('sender__username')
        .annotate(
            latest_message=Max('timestamp'),
            message_count=Count('id'),
            unread_count=Count('id', filter=Q(is_read=False))
        )
        .order_by('-latest_message')
    )

    for data in report_data:
        latest_message = Chat.objects.filter(
            sender__username=data['sender__username'], 
            receiver=current_user
        ).order_by('-timestamp').first()

        data['message_content'] = latest_message.message if latest_message else "No message content"
        data['time_sent'] = latest_message.timestamp if latest_message else None
        data['is_read'] = latest_message.is_read if latest_message else True

    return render(request, 'chat/message_report.html', {'report_data': report_data})

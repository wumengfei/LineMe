#!/usr/bin/env python
# coding: utf-8

from django.contrib.auth.decorators import login_required
from django.core.paginator import PageNotAnInteger
from django.core.paginator import Paginator, EmptyPage
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache

from LineMe.constants import PROJECT_NAME, CITIES_TABLE, PRIVACIES
from LineMe.settings import DEPLOYED_LANGUAGE
from LineMe.utils import get_template_dir
from friendnet.forms import *
from friendnet.methods.algorithm.recommender import Recommender
from friendnet.methods.algorithm.search import SearchEngine
from friendnet.methods.basic.avatar import handle_uploaded_avatar
from friendnet.methods.basic.egonet import get_user_ego_graph
from friendnet.methods.basic.globalnet import *
from friendnet.methods.basic.group import *
from friendnet.methods.basic.groupmember import *
from friendnet.methods.basic.link import *
from friendnet.methods.basic.profile import Profile
from friendnet.methods.basic.user import *
from friendnet.methods.checking import check_groupid
from friendnet.methods.utils import input_filter
from friendnet.models import Group, GroupMember, MemberRequest, Privacy
from iauth.methods.session import get_session_consume

# Todo: ///check all place with user input///, deal with utf-8 chinese, check all filter to get
# Todo: member in group multiple?
# Todo: cookie based first login
# Todo: check all places with .source/target_member

lang = DEPLOYED_LANGUAGE
template_dir = get_template_dir('friendnet')


def redirect2main(request):
    return redirect('home')


def view_404(request):
    context = {"project_name": PROJECT_NAME,
               "lang": lang}
    return render(request, '_404.html', context)


def search(request):

    if not request.user.is_authenticated():
        return HttpResponse(json.dumps([]))

    return HttpResponse(json.dumps(SearchEngine(request).search(5)))


########################################################################


@login_required
def home(request):
    logger.info(logger_join('Access', get_session_id(request)))

    user = request.user
    my_groups, in_groups = get_user_groups_split(user)
    msgs_count = get_user_msgs_count(user)
    rcmd_groups = Recommender(user).group()

    first_login = get_session_consume(request, 'new_login')

    context = {"project_name": PROJECT_NAME,
               "lang": lang,
               "user": user,
               "my_groups": my_groups,
               "in_groups": in_groups,
               "rcmd_groups": rcmd_groups,
               "msgs_count": msgs_count,
               "first_login": first_login,
               "group_created_status": 0,
               "identifier": IDENTIFIER,
               "group_cost": GROUP_CREATED_CREDITS_COST}

    if request.method == 'GET':
        return render(request, template_dir+'home.html', context)

    elif request.method == 'POST':
        gf = GroupCreateForm(request.POST)

        if gf.is_valid():
            name = gf.cleaned_data['name']
            identifier = int(gf.cleaned_data['identifier'])
            gtype = int(gf.cleaned_data['gtype'])

            status = create_group(request, user, name, identifier, gtype)
            context["group_created_status"] = status

            if status == 0:
                groupid = Group.objects.get(group_name=name.upper()).id
                return redirect('group', groupid=groupid)

            else:
                return render(request, template_dir+'home.html', context)

        context["group_created_status"] = -4
        return render(request, template_dir+'home.html', context)

    else:
        return HttpResponse(status=403)


@login_required
@never_cache
def msg_panel(request):
    user = request.user

    if request.is_ajax():

        page = request.GET.get('page')
        msgs, msg_index = get_user_msgs(user)
        paginator = Paginator(msgs, 10)

        try:
            p = paginator.page(page)
        except PageNotAnInteger:
            p = paginator.page(1)
        except EmptyPage:
            p = paginator.page(paginator.num_pages)

        my_members = GroupMember.objects.filter(user=user)

        msg_creators = {xp: GroupMember.objects.get(user=xp.creator, group=xp.group).member_name for xp in p}

        return render(request, template_dir+'home_msg.html',
                      {"msgs": p,
                       "msg_index": msg_index,
                       "my_members": my_members,
                       "msg_creators": msg_creators})

    else:
        return HttpResponse(status=403)


@login_required
def msg_handle(request, mtype='0', handleid=0):
    user = request.user

    if request.method == 'GET':

        if mtype == '1':
            status = link_confirm(request, user, get_link(int(handleid)))
        elif mtype == '0':
            status = link_reject(request, user, get_link(int(handleid)))

        # link aggregate
        elif mtype == '3':
            status = link_confirm_aggregate(request, user, get_link(int(handleid)))
        elif mtype == '2':
            status = link_reject_aggregate(request, user, get_link(int(handleid)))
        else:
            return HttpResponse(status=403)

        return HttpResponse(status, content_type='text/plain')

    elif request.is_ajax():
        links = request.POST.get('linkids')

        count = 0

        try:
            confirm_list = json.loads(links)
        except ValueError, e:
            pass
        else:
            for link in confirm_list:
                if link.isdigit():
                    status = link_confirm(request, user, get_link(int(link)))
                    if status == 0:
                        count += 1

        return HttpResponse(count, content_type='text/plain')

    else:
        return HttpResponse(status=403)


@login_required
def inv_panel(request):
    user = request.user

    if request.is_ajax():

        page = request.GET.get('page')
        group_name = input_filter(request.GET.get('groupname'))

        if group_name:
            invs = get_user_invs(user, group_name)
        else:
            invs = get_user_invs(user)

        paginator = Paginator(invs, 8)

        try:
            p = paginator.page(page)
        except PageNotAnInteger:
            p = paginator.page(1)
        except EmptyPage:
            p = paginator.page(paginator.num_pages)

        my_members = GroupMember.objects.filter(user=user)

        return render(request, template_dir+'home_inv.html', {"invs": p, "my_members": my_members})

    else:
        return HttpResponse(status=403)


# Todo: implement email sender
@login_required
def send_email2unconfirmed(request):
    return 0


########################################################################

@login_required
def ego_network(request, groupid=0):
    logger.info(logger_join('Access', get_session_id(request), gid=groupid))

    user = request.user
    groups = get_user_groups(user)
    rcmd_groups = Recommender(user).group()
    msgs_count = get_user_msgs_count(user)

    groupid = check_groupid(user, groupid)
    if groupid == 0:
        group = None
    else:
        group = get_object_or_404(Group, id=groupid)

    context = {"project_name": PROJECT_NAME,
               "lang": lang,
               "user": user,
               "groups": groups,
               "group": group,
               "rcmd_groups": rcmd_groups,
               "msgs_count": msgs_count}

    return render(request, template_dir+'ego.html', context)


@login_required
def ego_graph(request, groupid=0):
    user = request.user
    groupid = check_groupid(user, groupid)

    if groupid == 0 or groupid == -2:
        return JsonResponse({"nodes": None, "links": None}, safe=False)

    data = get_user_ego_graph(user, groupid)

    return HttpResponse(data)


@login_required
def rcmd_panel(request, groupid):
    user = request.user

    if request.is_ajax():

        page = request.GET.get('page')

        groupid = check_groupid(user, groupid)
        if groupid == 0:
            return render(request, template_dir+'ego_rcmd.html')

        # rcmd_gms = Recommender(user).simple(groupid)
        rcmd_gms = Recommender(user).friend(groupid)

        paginator = Paginator(rcmd_gms, 6)

        try:
            p = paginator.page(page)
        except PageNotAnInteger:
            p = paginator.page(1)
        except EmptyPage:
            p = paginator.page(paginator.num_pages)

        return render(request, template_dir+'ego_rcmd.html', {'members': p})

    else:
        return HttpResponse(status=403)


@login_required
def update_graph(request, groupid):
    user = request.user

    if request.is_ajax():
        new_links = request.POST.get('links')
        status = update_links(request, new_links, user, groupid)
        return HttpResponse(status, content_type='text/plain')

    else:
        return HttpResponse(status=403)


########################################################################

@login_required
def global_network(request, groupid=0):
    logger.info(logger_join('Access', get_session_id(request), gid=groupid))

    user = request.user
    groups = get_user_groups(user)
    msgs_count = get_user_msgs_count(user)
    groupid = check_groupid(user, groupid)

    context = {}
    if groupid == 0:
        group = None
    else:
        group = get_object_or_404(Group, id=groupid)
        info = get_user_global_info(user, groupid)
        context.update(info)

    context.update({"project_name": PROJECT_NAME,
                    "lang": lang,
                    "user": user,
                    "groups": groups,
                    "group": group,
                    "msgs_count": msgs_count})

    return render(request, template_dir+'global.html', context)


@login_required
def global_graph(request, groupid=0):
    user = request.user
    groupid = check_groupid(user, groupid)

    if groupid == 0:
        return JsonResponse({"nodes": None, "links": None}, safe=False)

    data = get_user_global_graph(user, groupid)
    # get_user_global_basic(user, groupid)
    # data = cache.get_or_set('globalnet', get_user_global_graph, user, groupid)
    return JsonResponse(data, safe=False)


@login_required
def global_map(request, groupid=0):
    user = request.user
    groupid = check_groupid(user, groupid)

    if groupid == 0:
        return JsonResponse({"nodes": None, "links": None}, safe=False)

    data = get_user_global_map(user, groupid)
    # data = cache.get_or_set('globalmap', get_user_global_map, user, groupid)
    return JsonResponse(data, safe=False)


@login_required
def global_three(request, groupid=0):
    user = request.user
    groupid = check_groupid(user, groupid)

    if groupid == 0:
        return JsonResponse({"nodes": None, "links": None}, safe=False)

    data = get_user_global_three(user, groupid)
    return JsonResponse(data, safe=False)


########################################################################

@login_required
def profile(request):
    logger.info(logger_join('Access', get_session_id(request)))

    user = request.user
    username = get_user_name(user)
    msgs_count = get_user_msgs_count(user)

    first_login = request.session.get('new_login')

    if user.extra.location:
        country, city = user.extra.location.split('-')
    else:
        country, city = "", ""

    context = {"project_name": PROJECT_NAME,
               "lang": lang,
               "user": user,
               "username": username,
               "msgs_count": msgs_count,
               "first_login": first_login,
               "cities_table": CITIES_TABLE,
               "country": country,
               "city": city}

    if request.method == 'GET':
        return render(request, template_dir+'profile.html', context)

    elif request.is_ajax():
        # first_login = get_session_consume(request, 'new_login')

        pf = Profile(request)
        if pf.is_valid():
            if pf.update() == 0:
                if first_login:
                    create_avatar(request, user.id, username=get_user_name(user))
                return HttpResponse(0, content_type='text/plain')

        return HttpResponse(-1, content_type='text/plain')

    else:
        return HttpResponse(status=403)


########################################################################

@login_required
def settings(request):
    logger.info(logger_join('Access', get_session_id(request)))

    user = request.user

    if request.method == 'GET':
        msgs_count = get_user_msgs_count(user)

        pris = {}
        for i, pri in PRIVACIES.items():
            if getattr(user.privacy, pri[0].name):
                pris[i] = pri+(True,)
            else:
                pris[i] = pri+(False,)

        context = {"project_name": PROJECT_NAME,
                   "lang": lang,
                   "user": user,
                   "msgs_count": msgs_count,
                   "privacies": pris}

        return render(request, template_dir+'settings.html', context)

    else:
        return HttpResponse(status=403)


def privacy_save(request):
    logger.info(logger_join('Access', get_session_id(request)))

    user = request.user

    if request.is_ajax():
        try:
            for k, v in json.loads(request.POST.get('privacies')).items():
                a = PRIVACIES[k]

                pri = Privacy.objects.get(user=user)
                setattr(pri, a[0].name, v)
                pri.save()
        except Exception, e:
            logger.error(logger_join('Privacy', get_session_id(request), 'failed', e=e))
            return HttpResponse(-1, content_type='text/plain')

        logger.info(logger_join('Update', get_session_id(request)))
        return HttpResponse(0, content_type='text/plain')

    else:
        return HttpResponse(status=403)


########################################################################

@login_required
def avatar(request):
    logger.info(logger_join('Access', get_session_id(request)))

    user = request.user
    msgs_count = get_user_msgs_count(user)

    context = {"project_name": PROJECT_NAME,
               "user": user,
               "msgs_count": msgs_count}

    return render(request, 'friendnet/tests/avatar.html', context)


@login_required
def img_handle(request):
    if request.is_ajax():

        status = handle_uploaded_avatar(request)
        return HttpResponse(status, content_type='text/plain')

    else:
        return HttpResponse(status=403)


########################################################################

# Todo: learn from ego and global
@login_required
def manage_group(request, groupid=0):
    logger.info(logger_join('Access', get_session_id(request), gid=groupid))

    us = get_session_consume(request, 'update_status')
    nm = get_session_consume(request, 'error_name')

    user = request.user
    groups = get_user_groups(user)
    rcmd_groups = Recommender(user).group()
    msgs_count = get_user_msgs_count(user)

    group = get_object_or_404(Group, id=groupid)

    group_privacy_check(user, group)

    context = {"project_name": PROJECT_NAME,
               "lang": lang,
               "user": user,
               "group": group,
               "groups": groups,
               "rcmd_groups": rcmd_groups,
               "update_status": us,
               "name": nm,
               "msgs_count": msgs_count}

    if request.method == 'GET':
        if user != group.creator:
            members = GroupMember.objects.filter(group=group)
            members_count = members.count()

            follow_status = get_user_join_status(request, user, group)
            context.update({"creator": group.creator,
                            "members_count": members_count,
                            "follow_status": follow_status})

            return render(request, template_dir+'group2.html', context)

        else:

            mpage = request.GET.get('mpage')

            # Todo: implement request paginator
            rpage = request.GET.get('rpage')

            members = GroupMember.objects.filter(group=group).order_by('-created_time')
            request_members = MemberRequest.objects.filter(group=group).exclude(is_valid=False)
            paginator = Paginator(members, 15)

            try:
                p = paginator.page(mpage)
            except PageNotAnInteger:
                p = paginator.page(1)
            except EmptyPage:
                p = paginator.page(paginator.num_pages)

            members_count = members.count()
            context.update({"members": p,
                            "creator": user,
                            "members_count": members_count,
                            "requests": request_members})

            return render(request, template_dir+'group1.html', context)

    elif request.method == 'POST':
        gf = GroupMemberCreateForm(request.POST)

        if gf.is_valid():
            name = gf.cleaned_data['name']
            identifier = gf.cleaned_data['identifier']

            # Todo: impl over max-size
            status = create_group_member(request, group, name, identifier)

            if status != 0:
                request.session['error_name'] = name
                request.session['update_status'] = False
            else:
                request.session['update_status'] = True

            return redirect('group', groupid)

    else:
        return HttpResponse(status=403)


@login_required
def upload_members(request, groupid):
    user = request.user

    if Group.objects.filter(creator=user, id=groupid).exists():
        group = Group.objects.get(id=groupid)

        if request.method == 'POST':
            fuf = FileUploadForm(request.POST, request.FILES)
            if fuf.is_valid():

                status = create_group_member_from_file(request, group)
                if status != 0:
                    request.session['update_status'] = False
                    request.session['error_name'] = status
                    return redirect('group', groupid=groupid)
                else:

                    request.session['update_status'] = True
                    return redirect('group', groupid=groupid)
            else:
                request.session['update_status'] = False
                return redirect('group', groupid=groupid)

    else:
        return redirect('group', groupid=groupid)


# Todo: check check
@login_required
def join(request, groupid):

    """
    :param request:
    :param groupid:
    :return status code
     403: already in this group
     0: success
    -1: failed (already in)
    -2: member not existed
    -3: more than maxsize
    -4: internal error
    """

    user = request.user
    group = get_object_or_404(Group, id=groupid)

    group_privacy_check(user, group)

    # already in the group
    if get_user_join_status(request, user, group) == 1:
        return HttpResponse(status=403)

    if request.is_ajax():

        # no validation group, if i am not in this group, create and join
        if group.identifier == 2:
            if get_user_join_status(request, user, group) == 0:
                status = create_group_member(request,
                                             group,
                                             get_user_name(user),
                                             'no validation',
                                             user=user,
                                             is_joined=True)

                return HttpResponse(status, content_type='text/plain')

            else:
                logger.warning(logger_join('Join', get_session_id(request), 'failed', gid=group.id))
                return HttpResponse(-4, content_type='text/plain')

        elif group.identifier == 1:
            gm = get_member_in_group(user, group)

            if not gm:
                return HttpResponse(-2, content_type='text/plain')

            status = follow(request, user, group, user.email)
            if status != 0:
                logger.warning(logger_join('Join', get_session_id(request), 'failed', gid=group.id))

            return HttpResponse(status, content_type='text/plain')

        elif group.identifier == 0:
            gm = get_member_in_group(user, group)

            if not gm:
                return HttpResponse(-2, content_type='text/plain')
            else:
                return HttpResponse(-1, content_type='text/plain')

    elif request.method == 'POST':
        jf = JoinForm(request.POST)

        if jf.is_valid():
            identifier = jf.cleaned_data['identifier']

            if identifier != '':
                status = follow(request, user, group, identifier)
                if status == 0:
                    return redirect('egoId', groupid=groupid)

        request.session['join_failed'] = True
        logger.warning(logger_join('Join', get_session_id(request), 'failed', gid=group.id))
        return redirect('group', groupid=groupid)

    else:
        return HttpResponse(status=403)


@login_required
def join_request(request, groupid):

    user = request.user
    group = get_object_or_404(Group, id=groupid)

    group_privacy_check(user, group)

    if request.method == 'POST' and not GroupMember.objects.filter(user=user, group=group).exists():
        msg = request.POST.get('message')
        status = create_request(request, user, group, msg)
        return redirect('group', groupid=groupid)

    else:
        return HttpResponse(status=403)


# Todo: if the member is existed, sth is wrong
# Todo: impl join decline
@login_required
def join_confirm(request, groupid, requestid):

    user = request.user
    group = get_object_or_404(Group, id=groupid)

    if request.method == 'GET' and group.creator == user:

        mr = get_object_or_404(MemberRequest, id=requestid, group=group)
        mr.is_valid = False
        mr.save()

        status = create_group_member(request, group, get_user_name(mr.user), 'accepted', mr.user, is_joined=True)

        if status == 0:
            m = GroupMember.objects.get(group=group, user=user)
            m.is_joined = True
            m.save()
            return redirect('group', groupid)
        else:

            # Todo: confirm failed
            return redirect('group', groupid)

    else:
        return HttpResponse(status=403)


# Todo: impl decline
@login_required
def join_decline(request, groupid, requestid):
    return redirect('group', groupid)


########################################################################

@login_required
def exp(request, groupid):
    context = {'groupid': groupid}
    if request.method == 'GET':
        return render(request, 'friendnet/exp.html', context)


@login_required
def exp_data(request, groupid):
    data = get_user_global_exp(request.user, groupid)
    # print data
    return JsonResponse(data, safe=False)



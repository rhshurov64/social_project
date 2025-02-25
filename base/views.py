from django.shortcuts import render, redirect , HttpResponseRedirect, get_object_or_404
from django.contrib.auth.models import User, auth
from django.contrib import messages
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate,login,logout,update_session_auth_hash
from .models import *
from itertools import chain
import random
import uuid
from django.core.mail import send_mail
from django.conf import settings
from .forms import *
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.http import FileResponse
from django.utils import timezone
from chat.models import Notification




@login_required(login_url='/login/')
def index(request):
    data = User.objects.exclude(username = request.user).exclude(username = 'admin')
    status = Post.objects.all().order_by('-updated_at')
    user = request.user
    post = Post.objects.filter(username = user)
    total_post = len(post)
    comments = Comment.objects.all()
    postimg = []
    current_user = request.user
    profile = Profile.objects.get(user = current_user)
    
    
    if request.method == "POST":
        user = request.user
        author = User.objects.get(username = user)
        authorprofile = Profile.objects.get(user = user)
        text = request.POST['text']
        postimg = request.FILES.getlist('image', None)
        post = Post.objects.create(author = author, authorprofile = authorprofile, username = user, text=text)
        
        
        if post:
            if postimg:
                for image in postimg:
                    # print(image)
                    Image.objects.create(post = post, image = image)
            profile.total_post = profile.total_post + 1
            profile.save()
            
    
    user = request.user
    user_object = User.objects.get(username = user)
    user_profile = get_object_or_404(Profile, user=user)
    
    followers = user_profile.followers.all()
    follower_profile_object = None
    
    for follower in followers:
        follower_profile_object = Profile.objects.filter(user = follower)
        print(follower_profile_object)
    
    followings = user_profile.following.all()
    following_profile_object = None
    for following in followings:
        following_profile_object = Profile.objects.filter(user = following)
        print(following_profile_object)
        
    
    post_like = {}
    for post in status:
        likes = Like.objects.filter(post=post)
        post_like[post.id] = [like.user for like in likes]
        
    
    items = [1, 2, 3, 4, 5]  # Your list of items
    counter = 0
    
    return render(request,'base/home.html', {'counter':counter ,'items':items,'data':data, 'posts':status, 'total_post':total_post, 'comments': comments, 'user_profile': user_profile,'followers':followers, 'followings': followings, 'follower_profile_object': follower_profile_object, 'following_profile_object':following_profile_object, 'user_object':user_object, 'post_like':post_like})



def rendertosetting(request):
    return render(request,'base/render.html')


@login_required(login_url='/login/')
def user_logout(request):
    user = request.user
    user_obj = User.objects.get(username=user)
    status = OnlineStatus.objects.filter(user = user_obj).update(status ='offline')
    
    login_entry = UserLoginHistory.objects.filter(user=user_obj, logout_time__isnull = True).first()
    if login_entry:
        latest_login_entry = UserLoginHistory.objects.filter(user=user_obj, logout_time__isnull = True).order_by('-login_time').first()
        if latest_login_entry:
            latest_login_entry.logout_time = timezone.now()
            latest_login_entry.duration_minutes = (latest_login_entry.logout_time - latest_login_entry.login_time).total_seconds() / 60
            latest_login_entry.save()
    logout(request)
    return redirect('login')



def login(request):
    if not request.user.is_authenticated:
        if request.method == 'POST':
            un = request.POST['username']
            pw = request.POST['password']
            userr = auth.authenticate(username=un, password=pw)
            
            if userr is not None:
                if userr.is_staff == True:
                    auth.login(request, userr)
                    return redirect('index')
                else:
                    checkk = Verify_User.objects.get(username = un)
                    if checkk.check_user == True:
                        auth.login(request, userr)
                        user = request.user
                        user_obj = User.objects.get(username = user)
                        time = UserLoginHistory.objects.create(user = user_obj, login_time = timezone.now())
                        user_status = OnlineStatus.objects.get(user = user_obj)
                        if user_status:
                            user_status.status = 'online'
                            user_status.save()
                        return redirect('index')
                        
                        
                    else:
                        messages.warning(request,"Please Verify Your Account First!")
            else:
                messages.info(request, 'Credentials Invalid')
                return redirect('login')
    else:
        return redirect('index')
    return render(request,'base/login.html')


@login_required(login_url='/login/')
def like_post(request, post_id):
    post = Post.objects.get(id=post_id)
    user = request.user
    # username = user.username
    
    if Like.objects.filter(user=user, post=post).exists():
        Like.objects.filter(user=user, post=post).delete()
        post.likes.remove(user)
        post.total_like -= 1
        post.save()
    else:
        like = Like(user=user, post=post)
        like.save()
        post.likes.add(user)
        post.total_like += 1
        post.save()
        if user != post.author:
            Notification.objects.create(receiver=post.author, sender =user,like_notifcation= True, post_id=post_id,  message=f'{user.get_full_name()} Liked Your Post')
        
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

@login_required(login_url='/login/')
def like_list(request, post_id):
    post = Post.objects.get(id = post_id)
    return render(request, 'base/react_list.html', {'post':post})


@login_required(login_url='/login/')
def postdelete(request):
    user = request.user
    profile = Profile.objects.get(user = user)
    post_id = request.GET.get('post_id')
    post = Post.objects.get(id=post_id)
    post.delete()
    profile.total_post = profile.total_post - 1
    profile.save()
    
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

@login_required(login_url='/login/')
def comment_delete(request):
    cmnt_id = request.GET.get('cmnt_id')
    post_id = request.GET.get('post_id')
    cmnt = Comment.objects.get(id = cmnt_id)
    cmnt.delete()
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


@login_required(login_url='/login/')
def replay_delete(request):
    replay_id = request.GET.get('replay_id')
    replay = Replay.objects.get(id = replay_id)
    replay.delete()
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


@login_required(login_url='/login/')
def profile_post_delete(request):
    user = request.user
    profile = Profile.objects.get(user = user)
    post_id = request.GET.get('post_id')
    post = Post.objects.get(id=post_id)
    post.delete()
    profile.total_post = profile.total_post - 1
    profile.save()
    
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


def signup(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        password = request.POST['password1']
        password2 = request.POST['password2']

        if password == password2:
            # if User.objects.filter(email=email).exists():
            #     messages.info(request, 'Email Taken')
            #     return redirect('signup')
            if User.objects.filter(username=username).exists():
                messages.info(request, 'Username Taken')
                return redirect('signup')
            else:
                user = User.objects.create_user(username=username, email=email, password=password, first_name=first_name, last_name=last_name )
                # user.save()
                
               
                
                u_id = str(uuid.uuid4())
                pro_obj = Verify_User.objects.create(user = user, username=username, token = u_id)
                sendemail(email, u_id)
                messages.success(request,'Registration Success, Verification link send in your email. Please Verify Your account!')
                user_login = auth.authenticate(username=username, password=password)
                auth.login(request, user_login)
                return redirect('signup') 
                
        else:
            messages.info(request, 'Password Not Matching')
            return redirect('signup')
        
    else:
        return render(request, 'base/signUp.html')

    
def sendemail(email,token):
    subject = 'Verify Email'
    message = f'Click on the link to verify your Account - http://127.0.0.1:8000/verify/{token}'
    print(message)
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [email]
    send_mail(subject=subject,message=message,from_email=from_email,recipient_list=recipient_list)
    
    
def account_verify(request,token):
    pf = Verify_User.objects.filter(token = token).first()
    pf.check_user = True
    pf.save()
    messages.success(request,'Your Account is verifed, Please Complete your Profile!')
    return render(request, 'base/render.html')

    
@login_required(login_url='/login/')
def setting(request):
    if request.method == 'POST':
        user = request.user
        # print(user)
        userr = User.objects.get(username = user)
        image = request.FILES['image']
        bio = request.POST['bio']
        about = request.POST['about']
        location = request.POST['location']
        country = request.POST['country']
        facebook = request.POST['facebook']
        twitter = request.POST['twitter']
        linkdin = request.POST['linkdin']
        github = request.POST['github']
        new_profile = Profile.objects.create(user=userr, bio = bio, about = about, profileimg = image, location = location, country = country, facebook = facebook, twitter = twitter, linkdin = linkdin, github = github)
        new_profile.save()
        # new_profile = Profile.objects.filter(pk = userr.pk).update(bio = bio, profileimg = image, location = location)
        return redirect('index')
    return render(request, 'base/setting.html')


@login_required(login_url='/login/')
def profile(request, id):
    user_data = User.objects.get(id = id)
    profile_data = Profile.objects.get(user = user_data)
    posts = Post.objects.filter(author = user_data).order_by('-created_at')
    post_length = len(posts)
    
    user = get_object_or_404(User, id=id)
    user_profile_check = get_object_or_404(Profile, user=user)
    
    followers_check = user_profile_check.followers.all()
    
    follow_check = False
    for follower in followers_check:
        if request.user == follower:
            follow_check = True
            break
        else:
            follow_check = False
    
    
    context = {
        "udata" : user_data,
        "profile_data" : profile_data,
        'posts' : posts,
        'post_length' : post_length,
        'follow_check': follow_check,
    }
    return render(request,'base/profile.html',context)


@login_required(login_url='/login/')
def suggestion(request):
    if 'search_box' in request.GET:
        key = request.GET['search_box']
        data = User.objects.filter(Q(first_name__icontains = key)| Q(last_name__icontains = key)).exclude(username = 'admin').exclude(username = request.user)
    else:
        data = User.objects.exclude(username = request.user).exclude(username = 'admin')
    return render(request,'base/suggestion.html',{'data':data})


@login_required(login_url='/login/')
def update(request,id):
    if request.method =='POST':
        pi = Profile.objects.get(pk= id)
        fm = ProfileForm(request.POST, request.FILES, instance=pi)
        if fm.is_valid():
            fm.save()
    else:
        pi = Profile.objects.get(pk= id)
        fm = ProfileForm(instance=pi)
        
    return render(request,'base/update.html',{'form':fm})


@login_required(login_url='/login/')
def profile_image_update(request,id):
    if request.method =='POST':
        pi = Profile.objects.get(pk= id)
        fm = ProfileImageForm(request.POST, request.FILES, instance=pi)
        if fm.is_valid():
            fm.save()
    else:
        pi = Profile.objects.get(pk= id)
        fm = ProfileImageForm(instance=pi)
        
    return render(request,'base/profileimageedit.html',{'form':fm})



def name_edit(request,id):
    if request.method =='POST':
        pi = User.objects.get(pk= id)
        fm = UserDataForm(request.POST, instance=pi)
        if fm.is_valid():
            fm.save()
    else:
        pi = User.objects.get(pk= id)
        fm = UserDataForm(instance=pi)
        
    return render(request,'base/nameedit.html',{'form':fm})



# @login_required(login_url='/login/')
# def postedit(request, id):
#     if request.method =='POST':
#         pi = Post.objects.get(pk= id)
#         fm = PostForm(request.POST, request.FILES, instance=pi)
#         if fm.is_valid():
#             fm.save()
#     else:
#         pi = Post.objects.get(pk= id)
#         fm = PostForm(instance=pi)
#     return render(request,'base/postedit.html',{'form':fm})


def postedit(request, id):
    post = get_object_or_404(Post, pk=id)

    if request.method == 'POST':
        form = PostForm(request.POST, instance=post)
        formset = ImageFormSet(request.POST, request.FILES, instance=post)

        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
        else:
            print("Form errors:", form.errors)
            print("Formset errors:", formset.errors)
    else:
        form = PostForm(instance=post)
        formset = ImageFormSet(instance=post)

    return render(request, 'base/postedit.html', {'form': form, 'formset': formset, 'post': post})



@login_required(login_url='/login/')
def commentedit(request, id):
    if request.method =='POST':
        pi = Comment.objects.get(pk= id)
        fm = CommentForm(request.POST, instance=pi)
        if fm.is_valid():
            fm.save()
    else:
        pi = Comment.objects.get(pk= id)
        fm = CommentForm(instance=pi)
    return render(request,'base/commentedit.html',{'form':fm})


@login_required(login_url='/login/')
def replayedit(request, id):
    if request.method =='POST':
        pi = Replay.objects.get(pk= id)
        fm = ReplayForm(request.POST, instance=pi)
        if fm.is_valid():
            fm.save()
    else:
        pi = Replay.objects.get(pk= id)
        fm = ReplayForm(instance=pi)
    return render(request,'base/replayedit.html',{'form':fm})




@login_required(login_url='/login/')
def comment(request, id):
    if request.method == 'POST':
        text = request.POST['comment']
        user = request.user
        author = User.objects.get(username = user)
        authorprofile = Profile.objects.get(user = user)
        
        post_obj = Post.objects.get(id = id)
        
        comment = Comment.objects.create(author= author, authorprofile =authorprofile, post = post_obj, text = text)
        if comment:
            post_obj.total_comment= post_obj.total_comment + 1
            post_obj.save()
            if user != post_obj.author:
                Notification.objects.create(receiver=post_obj.author, sender =user, comment_notifcation= True, post_id=id,  message=f'{user.get_full_name()} Comment on Your Post')
    return HttpResponseRedirect(f'show_comment/{id}')


@login_required(login_url='/login/')
def show_comment(request, id):
    post = Post.objects.filter(id = id).order_by('-created_at')
    comments = Comment.objects.filter(post__in= post).order_by('-created_at')
    return render(request, 'base/comment.html', {'posts':post, 'comments': comments})


@login_required(login_url='/login/')
def show_replay(request, pid, cid):
    
    post = Post.objects.filter(id = pid)
    comments = Comment.objects.filter(id= cid)
    replays = Replay.objects.filter(comment__in = comments)
    
    if request.method == 'POST':
        replay = request.POST['replay']
        user = request.user
        author = User.objects.get(username = user)
        authorprofile = Profile.objects.get(user = user)
        posts = Post.objects.get(id = pid)
        cmnt = Comment.objects.get(id = cid)
        replay = Replay.objects.create(author= author, authorprofile =authorprofile,post = posts, comment = cmnt, replay = replay)
        
        if user != cmnt.author:
            Notification.objects.create(receiver=cmnt.author, sender =user, replay_notifcation= True, post_id=pid, comment_id = cid,  message=f'{user.get_full_name()} Replay on Your Comment')
        
        if replay:
            posts.total_comment= posts.total_comment + 1
            posts.save()
            
    
    return render(request, 'base/replay.html', {'posts':post, 'comments': comments, 'replays':replays})
    
    
    
@login_required(login_url='/login/')
def blocklist(request, bid):
    user = request.user.username
    author = User.objects.get(username = user)
    authorprofile = Profile.objects.get(user = author)
    
    blocked_user = User.objects.get(id = bid)
    blocked_user_profile = Profile.objects.get(user = blocked_user)
    blk = Block.objects.create(author = author,authorprofile= authorprofile, blocked_user =blocked_user,blocked_user_profile=blocked_user_profile, is_block= True)
    
    authorprofile.blocklist.add(blocked_user)
    
    if blocked_user in authorprofile.following.all():
        authorprofile.following.remove(blocked_user)
        
    if author in blocked_user_profile.following.all():
        blocked_user_profile.following.remove(author)
        
    if blocked_user in authorprofile.followers.all():
        authorprofile.followers.remove(blocked_user)
        
    if author in blocked_user_profile.followers.all():
        blocked_user_profile.followers.remove(author)
        
    return redirect('/')



@login_required(login_url='/login/')
def unblock(request, block_user_id):
    user = request.user
    author = User.objects.get(username = user)
    authorprofile = Profile.objects.get(user = author)
    
    
    blocked_user = User.objects.get(id = block_user_id)
    unblock_user = Block.objects.get(Q(author = user) & Q(blocked_user = blocked_user))
    if unblock_user:
        unblock_user.delete()
        authorprofile.blocklist.remove(blocked_user)
    return redirect('showblocklist')


@login_required(login_url='/login/')
def showblocklist(request):
    author = request.user
    users = Block.objects.filter(author = author)
    return render(request, 'base/blocklist.html', {'users' : users,})
    
    
    
@login_required(login_url='/login/')   
def download_image(request, image_id):
    image = get_object_or_404(Image, pk=image_id)
    image_path = image.image.path
    response = FileResponse(open(image_path, 'rb'))
    return response



    
    
@login_required(login_url='/login/')
def reports(request, username):
    user = User.objects.get(username = username)
    overview = Profile.objects.get(user = user)
    
    posts = Post.objects.filter(authorprofile = overview)
    
    total_comments = 0
    for post in posts:
       total_comments +=  post.total_comment

    likes = Like.objects.filter(post__in =posts)
    total_likes = len(likes)
    
    # log_history = UserLoginHistory.objects.filter(user = user, login_time__isnull = False, logout_time__isnull = False)
    log_history = UserLoginHistory.objects.filter(user = user)
    
    
    context = {
        'overview': overview,
        'total_likes': total_likes,
        'comment': comment,
        'total_comments': total_comments,
        'posts': posts,
        'log_history': log_history,
        
    }
    
    return render(request, 'base/reports.html', context)


@login_required(login_url='/login/')
def follow_user(request, user_id):
    user_to_follow = get_object_or_404(User, id=user_id)
    
    try:
        user_profile = Profile.objects.get(user=request.user)
    except Profile.DoesNotExist:
        pass
    
    user_to_unfollow = get_object_or_404(User, id=user_id)

    if user_to_follow != request.user and user_to_follow not in user_profile.following.all():
        user_profile.following.add(user_to_follow)
        user_to_follow_profile = Profile.objects.get(user=user_to_follow)
        user_to_follow_profile.followers.add(request.user)
        Notification.objects.create(receiver=user_to_follow, sender =request.user ,follow_notifcation= True, message=f'{request.user.get_full_name()} Follow You')
        
    elif user_to_unfollow != request.user and user_to_unfollow in user_profile.following.all():
        user_profile.following.remove(user_to_unfollow)
        user_to_unfollow_profile = Profile.objects.get(user=user_to_unfollow)
        user_to_unfollow_profile.followers.remove(request.user)
        
    user = get_object_or_404(User, id=user_id)
    user_profile_check = get_object_or_404(Profile, user=user)
    
    followers_check = user_profile_check.followers.all()
    
    # followers_check = user_profile_check.followers.all()
    
    follow_check = False
    for follower in followers_check:
        if request.user == follower:
            follow_check = True
            break
        else:
            follow_check = False

    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'), {'follow_check':follow_check})



@login_required(login_url='/login/')
def suggestion_follow_user(request, user_id):
    user_to_follow = get_object_or_404(User, id=user_id)
    
    try:
        user_profile = Profile.objects.get(user=request.user)
    except Profile.DoesNotExist:
        pass
    
    user_to_unfollow = get_object_or_404(User, id=user_id)

    if user_to_follow != request.user and user_to_follow not in user_profile.following.all():
        user_profile.following.add(user_to_follow)
        user_to_follow_profile = Profile.objects.get(user=user_to_follow)
        user_to_follow_profile.followers.add(request.user)
        
    elif user_to_unfollow != request.user and user_to_unfollow in user_profile.following.all():
        user_profile.following.remove(user_to_unfollow)
        user_to_unfollow_profile = Profile.objects.get(user=user_to_unfollow)
        user_to_unfollow_profile.followers.remove(request.user)
        
    user = get_object_or_404(User, id=user_id)
    user_profile_check = get_object_or_404(Profile, user=user)
    
    followers_check = user_profile_check.followers.all()

    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))





@login_required(login_url='/login/')
def follower_list(request, user_id):
    userr = get_object_or_404(User, id=user_id)
    user_profile = get_object_or_404(Profile, user=userr)
    
    if 'search_box' in request.GET:
        key = request.GET['search_box']
        followers = user_profile.followers.filter(Q(first_name__icontains =key)|Q(last_name__icontains =key))
    else:
        followers = user_profile.followers.all()
    
    profile_object = None
    for follower in followers:
        profile_object = Profile.objects.filter(user = follower)
        
    followers_check = user_profile.followers.all()
    follow_check = False
    for follower in followers_check:
        if request.user == follower:
            follow_check = True
            break
        else:
            follow_check = False
    
    # print([f"{key}: {value}" for key, value in followers.__dict__.items()])
    
    return render(request, 'base/follower_list.html', {'user_profile': user_profile, 'followers': followers, 'profile_object':profile_object, 'follow_check': follow_check})



@login_required(login_url='/login/')
def following_list(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user_profile = get_object_or_404(Profile, user=user)
    
    if 'search_box' in request.GET:
        key = request.GET['search_box']
        followings = user_profile.following.filter(Q(first_name__icontains =key)|Q(last_name__icontains =key))
    else:
        followings = user_profile.following.all()
    
    profile_object = None

    for following in followings:
        profile_object = Profile.objects.filter(user = following)
    
    return render(request, 'base/following_list.html', {'user_profile': user_profile, 'followings': followings, 'profile_object': profile_object})



def reset_password(request):
    if request.method == 'POST':
        email = request.POST['email']
        username = request.POST['username']
        passsword1 = request.POST['passsword']
        passsword2 = request.POST['passsword_']
        
        user_obj = User.objects.filter(username = username, email = email)
        if user_obj:
            if passsword1 == passsword2:
                user_obj = User.objects.get(username = username, email = email)
                user_obj.set_password(passsword1)
                user_obj.save()
                messages.success(request,"Password Changed!")
            else:
                messages.success(request,"Password Not Match!")
        else:
            messages.success(request,"Your Don't have any Account, Please create your account!")
        # print(email, username, passsword1, passsword2)
    return render(request, 'base/reset.html')


@login_required(login_url='/login/')
def delete_account(request):
    username = request.user.username
    # print(username)
    user_object = User.objects.get(username = username)
    # print(user_object)
    user_object.delete()
    return redirect('/login/')

    
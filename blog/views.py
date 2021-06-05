from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Count, Q
from django.http import Http404
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.views.generic.edit import CreateView

from blog.forms import CommentForm, ReplyForm
from blog.models import Post, Category, Tag, Comment, Reply


class PostDetailView(DetailView):
    model = Post

    def get_object(self, queryset=None): # オーバーライド
        obj = super().get_object(queryset=queryset) # → get_queryset().filter(pk=pk)
        if not obj.is_public and not self.request.user.is_authenticated: # 非公開かつログインしてなければ
            raise Http404
        return obj
    


class IndexView(ListView):
    model = Post
    template_name = 'blog/index.html' # 使用テンプレートの指定
    paginate_by = 3 # ページネーション：1ページあたりに表示する数


class CategoryListView(ListView):
    queryset = Category.objects.annotate(
        num_post=Count('post', filter=Q(post__is_public=True))
    )
    # Q(post__is_public=True) → postオブジェクトのis_publicがTrueをカプセル化
    # Category.objects.annotte(Count('post')) → 各Categoryに紐づくPost数を取得。Count第二引数で条件追加。


class CategoryPostView(ListView):
    model = Post
    template_name = 'blog/category_post.html' # 使用テンプレートの指定

    def get_queryset(self): # オーバーライド
        category_slug = self.kwargs['category_slug'] # urls.pyから受け取った辞書型kwargs
        self.category = get_object_or_404(Category, slug=category_slug) # 条件に合うCategoryオブジェクトを取得。なければ404を返す。get_context_dataでも使用するため、インスタンス変数として定義。注意：self.categoryはCategory型。
        qs = super().get_queryset().filter(category=self.category) # super().get_queryset() → model.objects.all() → Post.objects.all()
        # category_slug(str型)からCategory型に変換するための一連の手続き。
        return qs
    
    def get_context_data(self, **kwargs): # オーバーライド
        context = super().get_context_data(**kwargs) # contextを取得
        context['category'] = self.category # categoryキーに値を追加。インスタンス変数なので参照可能。
        # テンプレートに値を渡すために必要な手続き。
        return context


class TagListView(ListView):
    queryset = Tag.objects.annotate(num_post=Count(
        'post', filter=Q(post__is_public=True)
    ))
    # Q(post__is_public=True) → postオブジェクトのis_publicがTrueをカプセル化
    # Tag.objects.annotte(Count('post')) → 各Tagに紐づくPost数を取得。Count第二引数で条件追加。


class TagPostView(ListView):
    model = Post
    template_name = 'blog/tag_post.html' # 使用テンプレートの指定

    def get_queryset(self): # オーバーライド
        tag_slug = self.kwargs['tag_slug'] # urls.pyから受け取った辞書型kwargs
        self.tag = get_object_or_404(Tag, slug=tag_slug) # 条件に合うTagオブジェクトを返す。なければ404エラー。get_context_dataでも使用するためインスタンス変数として定義。
        qs = super().get_queryset().filter(tags=self.tag) # super().queryset() → model.objects.all() → Post.objects.all()
        return qs
    
    def get_context_data(self, **kwargs): # オーバーライド
        context = super().get_context_data(**kwargs) # contextを取得
        context['tag'] = self.tag # tagキーに値を追加。
        return context


class SearchPostView(ListView):
    model = Post
    template_name = 'blog/search_post.html'
    paginate_by = 2 # ページネーション：1ページあたりに表示する数

    def get_queryset(self):
        query = self.request.GET.get('q', None) # GETリクエストでqパラメータを取得。値が存在しない場合はNoneを取得。
        lookups = (
            Q(title__icontains=query) |
            Q(content__icontains=query) |
            Q(category__name__icontains=query) |
            Q(tags__name__icontains=query)
        )
        if query is not None:
            qs = super().get_queryset().filter(lookups).distinct() # distinctは検索結果の重複を削除するために使う。
            return qs
        qs = super().get_queryset()
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('q')
        context['query'] = query
        return context


class CommentFormView(CreateView):
    model = Comment
    form_class = CommentForm

    def form_valid(self, form):
        comment = form.save(commit=False)
        post_pk = self.kwargs['pk']
        comment.post = get_object_or_404(Post, pk=post_pk)
        comment.save()
        return redirect('blog:post_detail', pk=post_pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post_pk = self.kwargs['pk']
        context['post'] = get_object_or_404(Post, pk=post_pk)
        return context


@login_required
def comment_approve(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    comment.approve()
    return redirect('blog:post_detail', pk=comment.post.pk)
 
 
@login_required
def comment_remove(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    comment.delete()
    return redirect('blog:post_detail', pk=comment.post.pk)


class ReplyFormView(CreateView):
    model = Reply
    form_class = ReplyForm

    def form_valid(self, form):
        reply = form.save(commit=False)
        comment_pk = self.kwargs['pk']
        reply.comment = get_object_or_404(Comment, pk=comment_pk)
        reply.save()
        return redirect('blog:post_detail', pk=reply.comment.post.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        comment_pk = self.kwargs['pk']
        context['comment'] = get_object_or_404(Comment, pk=comment_pk)
        return context


@login_required
def reply_approve(request, pk):
    reply = get_object_or_404(Reply, pk=pk)
    reply.approve()
    return redirect('blog:post_detail', pk=reply.comment.post.pk)


@login_required
def reply_remove(request, pk):
    reply = get_object_or_404(Reply, pk=pk)
    reply.delete()
    return redirect('blog:post_detail', pk=reply.comment.post.pk)
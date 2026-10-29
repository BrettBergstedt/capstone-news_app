from django import forms

from .models import Article, Newsletter


class ArticleSubmissionForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = ["title", "content"]


class NewsletterForm(forms.ModelForm):
    class Meta:
        model = Newsletter
        fields = ["title", "description", "articles"]
        widgets = {"articles": forms.CheckboxSelectMultiple}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["articles"].queryset = Article.objects.filter(approved=True)

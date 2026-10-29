"""Model forms used by the Daily Brief web interface.

Defines the forms that capture article submissions and newsletter creation.
Keeping them separate from the views lets field layout and validation rules
be read without also reading the request-handling logic.
"""

from django import forms

from .models import Article, Newsletter


class ArticleSubmissionForm(forms.ModelForm):
    """Form a journalist uses to submit an article for editorial review.

    Only the title and body are editable here. Approval status and authorship
    are set by the view, so a submitter cannot mark their own work as approved.
    """

    class Meta:
        model = Article
        fields = ["title", "content"]


class NewsletterForm(forms.ModelForm):
    """Form a publisher uses to assemble a newsletter from approved articles.

    The list of selectable articles is narrowed to approved ones when the form
    is built, so unreviewed submissions cannot reach subscribers.
    """

    class Meta:
        model = Newsletter
        fields = ["title", "description", "articles"]
        widgets = {"articles": forms.CheckboxSelectMultiple}

    def __init__(self, *args, **kwargs):
        """Restrict the articles choice field to approved articles only."""
        super().__init__(*args, **kwargs)
        self.fields["articles"].queryset = Article.objects.filter(approved=True)

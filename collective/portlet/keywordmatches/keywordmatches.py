from zope.interface import implements
from zope import schema
from zope.formlib import form
from zope.component import getMultiAdapter

from plone.portlets.interfaces import IPortletDataProvider
from plone.app.portlets.portlets import base
from plone.app.portlets.cache import render_cachekey
from plone.memoize import ram
from plone.memoize.compress import xhtml_compress
from plone.memoize.instance import memoize

from Acquisition import aq_inner

from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.CMFCore.utils import getToolByName

from collective.portlet.keywordmatches import KeywordMatchesMessageFactory as _

class IKeywordMatches(IPortletDataProvider):
    """A portlet

    It inherits from IPortletDataProvider because for this portlet, the
    data that is being rendered and the portlet assignment itself are the
    same.
    """
    
    count = schema.Int(title=_(u'Number of related items to display'),
                       description=_(u'How many related items to list.'),
                       required=True,
                       default=5)

    state = schema.Tuple(title=_(u"Workflow state"),
                         description=_(u"Items in which workflow state to show."),
                         default=('published', ),
                         required=True,
                         value_type=schema.Choice(
                             vocabulary="plone.app.vocabularies.WorkflowStates")
                         )


class Assignment(base.Assignment):
    """Portlet assignment.

    This is what is actually managed through the portlets UI and associated
    with columns.
    """

    implements(IKeywordMatches)

    def __init__(self, count=5, state=('published', )):
        self.count = count
        self.state = state

    @property
    def title(self):
        """This property is used to give the title of the portlet in the
        "manage portlets" screen.
        """
        return "Keyword Matches"

class Renderer(base.Renderer):
    """Portlet renderer.

    This is registered in configure.zcml. The referenced page template is
    rendered, and the implicit variable 'view' will refer to an instance
    of this class. Other methods can be added and referenced in the template.
    """
    
    #render = ViewPageTemplateFile('keywordmatches.pt')
    _template = ViewPageTemplateFile('keywordmatches.pt')

    @ram.cache(render_cachekey)
    def render(self):
        return xhtml_compress(self._template())

    @property
    def available(self):
        return len(self._data())

    def getRelatedItems(self):
        return self._data()

    def getAllRelatedItemsLink(self):
        portal_state = getMultiAdapter((self.context, self.request), name=u'plone_portal_state')
        portal_url = portal_state.portal_url()
        
        context = aq_inner(self.context)
        keywords = context.Subject()
        url = '%s/search?' % portal_url
        if type(keywords) is str:
            url = '%sSubject=%s' % (url, keywords)
        else:
            for keyword in keywords:
                url = '%sSubject:list=%s&' % (url, keyword)
        return url

    @memoize
    def _data(self):
        context = aq_inner(self.context)
        keywords = context.Subject()
        here_path = ('/').join(context.getPhysicalPath())
        catalog = getToolByName(context, 'portal_catalog')
        limit = self.data.count
        state = self.data.state
        extra_limit = limit + 1
        results = catalog(Subject=keywords,
                       review_state=state,
                       sort_on='Date',
                       sort_order='reverse',
                       sort_limit=extra_limit)
        return [res for res in results if res.getPath() != here_path][:limit]

class AddForm(base.AddForm):
    """Portlet add form.

    This is registered in configure.zcml. The form_fields variable tells
    zope.formlib which fields to display. The create() method actually
    constructs the assignment that is being added.
    """
    form_fields = form.Fields(IKeywordMatches)
    label = _(u"Add Related Items Portlet")
    description = _(u"This portlet displays recent Related Items based on keywords matches.")

    def create(self, data):
        return Assignment(count=data.get('count', 5), state=data.get('state', ('published',)))

# NOTE: IF this portlet does not have any configurable parameters, you can
# remove this class definition and delete the editview attribute from the
# <plone:portlet /> registration in configure.zcml

class EditForm(base.EditForm):
    """Portlet edit form.

    This is registered with configure.zcml. The form_fields variable tells
    zope.formlib which fields to display.
    """
    form_fields = form.Fields(IKeywordMatches)
    label = _(u"Edit Related Items Portlet")
    description = _(u"This portlet displays recent Related Items based on keywords matches.")

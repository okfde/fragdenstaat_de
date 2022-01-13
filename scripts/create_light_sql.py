import re


ACCOUNT_CONSTRAINTS = re.compile(
    r'ALTER TABLE ONLY (?P<table>public\.\w+)\s+ADD CONSTRAINT (?P<constraint>["\w]+) FOREIGN KEY \((?P<fk>\w+)\) REFERENCES (?P<fk_table>public\.\w+)\((?P<field>\w+)\)(?P<tail>[^;]*);'
)

SQL_TEMPLATE = """
ALTER TABLE ONLY {table}
    DROP CONSTRAINT {constraint};
ALTER TABLE ONLY {table}
    ADD CONSTRAINT {constraint}
    FOREIGN KEY ({fk}) REFERENCES {fk_table}({field}) {on_delete}{tail};
"""

SAFE_TABLES = set(
    [
        "account_taggeduser",
        "account_user_groups",
        "account_user_user_permissions",
        "account_userpreference",
        "account_usertag",
        "auth_group",
        "auth_group_permissions",
        "auth_message",
        "auth_permission",
        "bootstrap4_alerts_bootstrap4alerts",
        "bootstrap4_badge_bootstrap4badge",
        "bootstrap4_card_bootstrap4card",
        "bootstrap4_card_bootstrap4cardinner",
        "bootstrap4_carousel_bootstrap4carousel",
        "bootstrap4_carousel_bootstrap4carouselslide",
        "bootstrap4_collapse_bootstrap4collapse",
        "bootstrap4_collapse_bootstrap4collapsecontainer",
        "bootstrap4_collapse_bootstrap4collapsetrigger",
        "bootstrap4_content_bootstrap4blockquote",
        "bootstrap4_content_bootstrap4code",
        "bootstrap4_content_bootstrap4figure",
        "bootstrap4_grid_bootstrap4gridcolumn",
        "bootstrap4_grid_bootstrap4gridcontainer",
        "bootstrap4_grid_bootstrap4gridrow",
        "bootstrap4_jumbotron_bootstrap4jumbotron",
        "bootstrap4_link_bootstrap4link",
        "bootstrap4_listgroup_bootstrap4listgroup",
        "bootstrap4_listgroup_bootstrap4listgroupitem",
        "bootstrap4_media_bootstrap4media",
        "bootstrap4_media_bootstrap4mediabody",
        "bootstrap4_picture_bootstrap4picture",
        "bootstrap4_tabs_bootstrap4tab",
        "bootstrap4_tabs_bootstrap4tabitem",
        "bootstrap4_utilities_bootstrap4spacing",
        "campaign_campaign",
        "cms_aliaspluginmodel",
        "cms_cmsplugin",
        "cms_globalpagepermission",
        "cms_globalpagepermission_sites",
        "cms_page",
        "cms_page_placeholders",
        "cms_pagepermission",
        "cms_pageuser",
        "cms_pageusergroup",
        "cms_placeholder",
        "cms_placeholderreference",
        "cms_staticplaceholder",
        "cms_title",
        "cms_treenode",
        "cms_urlconfrevision",
        "cms_usersettings",
        "cmsplugin_filer_image_filerimage",
        "comments_froidecomment",
        "contractor_contract",
        "contractor_contractworkplugin",
        "django_amenities_amenity",
        "django_celery_beat_clockedschedule",
        "django_celery_beat_crontabschedule",
        "django_celery_beat_intervalschedule",
        "django_celery_beat_periodictask",
        "django_celery_beat_periodictasks",
        "django_celery_beat_solarschedule",
        "django_comment_flags",
        "django_comments",
        "django_content_type",
        "django_flatpage",
        "django_flatpage_sites",
        "django_migrations",
        "django_redirect",
        "django_site",
        "djangocms_blog_authorentriesplugin",
        "djangocms_blog_authorentriesplugin_authors",
        "djangocms_blog_blogcategory",
        "djangocms_blog_blogcategory_translation",
        "djangocms_blog_blogconfig",
        "djangocms_blog_blogconfig_translation",
        "djangocms_blog_genericblogplugin",
        "djangocms_blog_latestpostsplugin",
        "djangocms_blog_latestpostsplugin_categories",
        "djangocms_blog_post",
        "djangocms_blog_post_categories",
        "djangocms_blog_post_related",
        "djangocms_blog_post_sites",
        "djangocms_blog_post_translation",
        "djangocms_icon_icon",
        "djangocms_link_link",
        "djangocms_picture_picture",
        "djangocms_text_ckeditor_text",
        "djangocms_video_videoplayer",
        "djangocms_video_videosource",
        "djangocms_video_videotrack",
        "easy_thumbnails_source",
        "easy_thumbnails_thumbnail",
        "easy_thumbnails_thumbnaildimensions",
        "fds_blog_article_categories",
        "fds_blog_article_related",
        "fds_blog_article_sites",
        "fds_blog_articleauthorship",
        "fds_blog_articletag",
        "fds_blog_author",
        "fds_blog_category",
        "fds_blog_category_translation",
        "fds_blog_latestarticlesplugin",
        "fds_blog_latestarticlesplugin_authors",
        "fds_blog_latestarticlesplugin_categories",
        "fds_blog_latestarticlesplugin_tags",
        "fds_blog_taggedarticle",
        "fds_cms_collapsiblecmsplugin",
        "fds_cms_designcontainercmsplugin",
        "fds_cms_documentcollectionembedcmsplugin",
        "fds_cms_documentembedcmsplugin",
        "fds_cms_documentpagescmsplugin",
        "fds_cms_documentportalembedcmsplugin",
        "fds_cms_fdspageextension",
        "fds_cms_foirequestlistcmsplugin",
        "fds_cms_foirequestlistcmsplugin_tags",
        "fds_cms_modalcmsplugin",
        "fds_cms_oneclickfoirequestcmsplugin",
        "fds_cms_pageannotationcmsplugin",
        "fds_cms_primarylinkcmsplugin",
        "fds_cms_sharelinkscmsplugin",
        "fds_cms_slidercmsplugin",
        "fds_cms_svgimagecmsplugin",
        "fds_cms_vegachartcmsplugin",
        "fds_donation_donationformcmsplugin",
        "fds_donation_donationgift",
        "fds_donation_donationgiftformcmsplugin",
        "fds_donation_donationprogressbarcmsplugin",
        "fds_donation_donor_subscriptions",
        "fds_donation_donortag",
        "fds_donation_taggeddonor",
        "fds_mailing_emailactioncmsplugin",
        "fds_mailing_emailheadercmsplugin",
        "fds_mailing_emailsectioncmsplugin",
        "fds_mailing_emailstorycmsplugin",
        "fds_mailing_emailtemplate",
        "fds_newsletter_newsletter",
        "fds_newsletter_newslettercmsplugin",
        "fds_newsletter_subscribertag",
        "fds_newsletter_taggedsubscriber",
        "filer_clipboard",
        "filer_clipboarditem",
        "filer_file",
        "filer_folder",
        "filer_folderpermission",
        "filer_image",
        "filer_thumbnailoption",
        "filingcabinet_collectiondirectory",
        "filingcabinet_collectiondocument",
        "filingcabinet_documentportal",
        "filingcabinet_page",
        "filingcabinet_pageannotation",
        "filingcabinet_taggeddocument",
        "foirequest_deliverystatus",
        "foirequest_foiattachment",
        "foirequest_foievent",
        "foirequest_foimessage",
        "foirequest_foiproject_publicbodies",
        "foirequest_messagetag",
        "foirequest_publicbodysuggestion",
        "foirequest_requestdraft",
        "foirequest_requestdraft_publicbodies",
        "foirequest_taggedfoiproject",
        "foirequest_taggedfoirequest",
        "foirequest_taggedmessage",
        "foirequestfollower_foirequestfollower",
        "foisite_foisite",
        "froide_campaign_answer",
        "froide_campaign_campaign",
        "froide_campaign_campaign_categories",
        "froide_campaign_campaign_translation",
        "froide_campaign_campaigncategory",
        "froide_campaign_campaigncategory_translation",
        "froide_campaign_campaigncmsplugin",
        "froide_campaign_campaignpage",
        "froide_campaign_campaignpage_campaigns",
        "froide_campaign_campaignprogresscmsplugin",
        "froide_campaign_campaignquestionairecmsplugin",
        "froide_campaign_campaignrequestscmsplugin",
        "froide_campaign_campaignsubscription",
        "froide_campaign_informationobject",
        "froide_campaign_informationobject_categories",
        "froide_campaign_informationobject_documents",
        "froide_campaign_informationobject_foirequests",
        "froide_campaign_informationobject_translation",
        "froide_campaign_question",
        "froide_campaign_questionaire",
        "froide_campaign_report",
        "froide_crowdfunding_contribution",
        "froide_crowdfunding_crowdfunding",
        "froide_crowdfunding_crowdfundingcontributorscmsplugin",
        "froide_crowdfunding_crowdfundingformcmsplugin",
        "froide_crowdfunding_crowdfundingprogresscmsplugin",
        "froide_exam_curriculum",
        "froide_exam_curriculum_jurisdictions",
        "froide_exam_curriculum_subjects",
        "froide_exam_examrequest",
        "froide_exam_privatecopy",
        "froide_exam_state",
        "froide_exam_subject",
        "froide_fax_signature",
        "froide_food_foodauthoritystatus",
        "froide_food_foodauthoritystatus_publicbodies",
        "froide_food_foodsafetyreport",
        "froide_food_venuerequest",
        "froide_food_venuerequestitem",
        "froide_legalaction_instance",
        "froide_legalaction_lawsuit",
        "froide_legalaction_proposal",
        "froide_legalaction_proposaldocument",
        "frontpage_featuredrequest",
        "geography_columns",
        "geometry_columns",
        "georegion_georegion",
        "guide_action",
        "guide_guidance",
        "guide_rule",
        "guide_rule_actions",
        "guide_rule_categories",
        "guide_rule_jurisdictions",
        "guide_rule_publicbodies",
        "letter_lettertemplate",
        "menus_cachekey",
        "problem_problemreport",
        "publicbody_categorizedpublicbody",
        "publicbody_category",
        "publicbody_classification",
        "publicbody_foilaw",
        "publicbody_foilaw_combined",
        "publicbody_foilaw_translation",
        "publicbody_jurisdiction",
        "publicbody_publicbody",
        "publicbody_publicbody_laws",
        "publicbody_publicbody_regions",
        "publicbody_publicbodytag",
        "publicbody_taggedpublicbody",
        "social_auth_association",
        "social_auth_nonce",
        "social_auth_usersocialauth",
        "sortabletable_datarow",
        "sortabletable_dataset",
        "sortabletable_sortabletableplugin",
        "spatial_ref_sys",
        "taggit_tag",
        "taggit_taggeditem",
        "team_team",
        "team_teammembership",
    ]
)


def print_constraints(constraint_sql, on_delete):
    matches = ACCOUNT_CONSTRAINTS.findall(constraint_sql)

    for match in matches:
        table, constraint, fk, fk_table, field, tail = match
        sql = SQL_TEMPLATE.format(
            table=table,
            constraint=constraint,
            fk=fk,
            fk_table=fk_table,
            field=field,
            on_delete=on_delete,
            tail=tail,
        )
        print(sql)


TABLE_RE = re.compile(r"CREATE TABLE public\.(\w+) ")


def main():

    # 1. pg_dump fragdenstaat_de --schema-only > schema.sql
    # 2. DROP old fragdenstaat_de_light:
    # psql -U postgres -c "DROP DATABASE IF EXISTS fragdenstaat_de_light;"
    # 3. Copy database:
    # psql -U postgres -c "CREATE DATABASE fragdenstaat_de_light WITH TEMPLATE fragdenstaat_de OWNER fragdenstaat_de;"
    # 4. python create_light_sql.py > make_light.sql
    # 5. psql fragdenstaat_de_light < make_light.sql
    # 6. pg_dump fragdenstaat_de_light | gzip -c > fragdenstaat_light.sql.gz

    with open("schema.sql") as f:
        constraint_sql = f.read()

    all_tables = TABLE_RE.findall(constraint_sql)

    print_constraints(constraint_sql, "ON DELETE CASCADE ")

    PARTIAL_TABLES = [
        (
            "account_user",
            "email NOT LIKE '%@okfn.de' OR private = TRUE OR email IS NULL; UPDATE account_user SET password='';",
        ),
        ("document_document", "user_id IS NULL;"),
        (
            "document_document",
            "id NOT IN (SELECT id FROM document_document ORDER BY id DESC LIMIT 500);",
        ),
        ("document_documentcollection", "user_id IS NULL;"),
        ("fds_donation_donor", "user_id IS NULL;"),
        ("fds_donation_donation", "donor_id IS NULL;"),
        ("foirequest_foirequest", "public = FALSE;"),
        ("foirequest_foiproject", "public = FALSE;"),
        ("fds_blog_article", "start_publication IS NULL;"),
    ]
    PARTIAL_SAFE = set([x[0] for x in PARTIAL_TABLES])

    all_safe_tables = SAFE_TABLES | PARTIAL_SAFE

    for table, sql in PARTIAL_TABLES:
        # yes, allow sql injection here for update clause on account_user
        print("DELETE FROM %s WHERE %s" % (table, sql))

    for table in all_tables:
        if table not in all_safe_tables:
            print("DELETE FROM %s;" % table)

    print_constraints(constraint_sql, "")
    print("VACUUM FULL ANALYZE;")


if __name__ == "__main__":
    main()

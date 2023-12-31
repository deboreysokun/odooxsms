# -*- coding: utf-8 -*-

from odoo.exceptions import UserError, AccessError
from odoo.tests import common
from odoo.tools import frozendict


class TestCompanyCheck(common.TransactionCase):

    def setUp(self):
        super(TestCompanyCheck, self).setUp()
        self.company_a = self.env['res.company'].create({
            'name': 'Company A'
        })
        self.company_b = self.env['res.company'].create({
            'name': 'Company B'
        })
        self.parent_company_a_id = self.env['test_new_api.model_parent'].create({
            'name': 'M1',
            'company_id': self.company_a.id,
        })
        self.parent_company_b_id = self.env['test_new_api.model_parent'].create({
            'name': 'M2',
            'company_id': self.company_b.id,
        })

    def test_company_check_0(self):
        """ Check the option _check_company_auto is well set on records"""
        m1 = self.env['test_new_api.model_child'].create({'company_id': self.company_a.id})
        self.assertTrue(m1._check_company_auto)

    def test_company_check_1(self):
        """ Check you can create an object if the company are consistent"""
        self.env['test_new_api.model_child'].create({
            'name': 'M1',
            'company_id': self.company_a.id,
            'parent_id': self.parent_company_a_id.id,
        })

    def test_company_check_2(self):
        """ Check you cannot create a record if the company is inconsistent"""
        with self.assertRaises(UserError):
            self.env['test_new_api.model_child'].create({
                'name': 'M1',
                'company_id': self.company_b.id,
                'parent_id': self.parent_company_a_id.id,
            })

    def test_company_check_3(self):
        """ Check you can create a record with the inconsistent company if there are no check"""
        self.env['test_new_api.model_child_nocheck'].create({
            'name': 'M1',
            'company_id': self.company_b.id,
            'parent_id': self.parent_company_a_id.id,
        })

    def test_company_check_4(self):
        """ Check the company consistency is respected at write. """
        child = self.env['test_new_api.model_child'].create({
            'name': 'M1',
            'company_id': self.company_a.id,
            'parent_id': self.parent_company_a_id.id,
        })

        with self.assertRaises(UserError):
            child.company_id = self.company_b.id

        with self.assertRaises(UserError):
            child.parent_id = self.parent_company_b_id.id

        child.write({
            'parent_id': self.parent_company_b_id.id,
            'company_id': self.company_b.id,
        })

    def test_company_environment(self):
        """ Check the company context on the environment is verified. """

        self.company_c = self.env['res.company'].create({
            'name': 'Company C'
        })

        user = self.env['res.users'].create({
            'name': 'Test',
            'login': 'test',
            'company_id': self.company_a.id,
            'company_ids': (self.company_a | self.company_c).ids,
        })

        user = user.with_user(user).with_context(allowed_company_ids=[])

        # When accessing company/companies, check raises error if unauthorized/unexisting company.
        with self.assertRaises(AccessError):
            user.with_context(allowed_company_ids=[self.company_a.id, self.company_b.id, self.company_c.id]).env.companies

        with self.assertRaises(AccessError):
            user.with_context(allowed_company_ids=[self.company_b.id]).env.company

        with self.assertRaises(AccessError):
            # crap in company context is not allowed.
            user.with_context(allowed_company_ids=['company_qsdf', 'company564654']).env.companies

        # In sudo mode, context check is bypassed.
        companies = (self.company_a | self.company_b)
        self.assertEqual(
            user.sudo().with_context(allowed_company_ids=companies.ids).env.companies,
            companies
        )

        self.assertEqual(
            user.sudo().with_context(
                allowed_company_ids=[self.company_b.id, 'abc']).env.company,
            self.company_b
        )
        """
        wrong_env = user.sudo().with_context(
            allowed_company_ids=[self.company_a.id, self.company_b.id, 'abc'])
        wrong_env.env.companies.mapped('name')
        # Wrong SQL query due to wrong company id.
        """
        # Fallbacks when no allowed_company_ids context key
        self.assertEqual(user.env.company, user.company_id)
        self.assertEqual(user.env.companies, user.company_ids)

    def test_company_sticky_with_context(self):
        context = frozendict({'nothing_to_see_here': True})
        companies_1 = frozendict({'allowed_company_ids': [1]})
        companies_2 = frozendict({'allowed_company_ids': [2]})

        User = self.env['res.users'].with_context(context)
        self.assertEqual(User.env.context, context)

        User = User.with_context(**companies_1)
        self.assertEqual(User.env.context, dict(context, **companies_1))

        # 'allowed_company_ids' is replaced if present in keys
        User = User.with_context(**companies_2)
        self.assertEqual(User.env.context, dict(context, **companies_2))

        # 'allowed_company_ids' is replaced if present in new context
        User = User.with_context(companies_1)
        self.assertEqual(User.env.context, companies_1)

        # 'allowed_company_ids' is sticky
        User = User.with_context(context)
        self.assertEqual(User.env.context, dict(context, **companies_1))

    def test_company_check_no_access(self):
        """ Test that company_check validates correctly the companies on
        the different records, even if the use has no access to one of the
        records, example, a private address set by an onchange
        """

        user = self.env['res.users'].create({
            'name': 'My Classic User',
            'login': 'My Classic User',
            'groups_id': [(6, 0, self.env.ref('base.group_user').ids)],
        })

        with common.Form(self.env['test_new_api.model_private_address_onchange'].with_user(user)) as form:
            form.name = 'My Classic Name'
            form.company_id = self.env.user.company_id
            with self.assertRaises(AccessError):
                form.address_id.name
            form.save()

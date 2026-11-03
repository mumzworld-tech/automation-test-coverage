#!/usr/bin/env python3
"""Build mapping.json -- the source of truth linking TestMO cases to automated tests.

There is no fuzzy matching here, by design. Every link below was checked by
reading the automated test's docstring / allure title against the TestMO case's
summary and steps. The keyword matcher this file used to carry produced links
like "Checkout - Apple pay" -> test_uae_checkout_cod_normal_coupon, which is
exactly what a source of truth must not do.

Rules encoded here
------------------
* Refs are platform-qualified ("app::test_uae_cart_remove_item"). 10 test names
  exist in two files at once -- the app cart/checkout suites were ported from
  the web ones and kept their names -- so a bare name is ambiguous.
* status "full"    -- the case's scenarios are covered end to end.
  status "partial" -- part of the case is covered, or the only script that
                      covers it is skipped. `notes` says what is missing.
  status "none"    -- nothing covers it. `notes` may still explain why, or why a
                      previously-recorded link was removed.
* Scope: only cases flagged Automated = YES/NO count towards coverage
  (see parse_testmo_csv.py). "Not planned" cases keep their mapping but sit
  outside every percentage.
"""
import datetime as _dt
import json
import subprocess
from datetime import date
from pathlib import Path

HERE = Path(__file__).parent

# --------------------------------------------------------------------------
# mWEB -- release checklist, TestMO run 2154
# --------------------------------------------------------------------------
WEB_MAPPING = {
    # --- GeoIp / Store (all Not planned -> out of scope) -------------------
    "1018734": ("none", [],
        "Arabic IS exercised end to end: every suite runs a second time with LOCALE=ar, which "
        "routes to /ar, /sa-ar, /bh-ar, /kw-ar and /global-ar (FALCONS-330). What this case asks "
        "for -- using the in-page language switcher to move between stores -- is not automated; "
        "the locale is chosen when the session starts."),

    # --- Catalogue (all Not planned -> out of scope) -----------------------
    "1548291": ("partial", ["web_commons::test_web_filters_price_range"],
        "FALCONS-390 opens the Sale listing, drags the price ceiling down, and verifies the listing "
        "narrowed and every price respects it. The Category and Brand filters this case starts with "
        "are applied on a search listing in the same suite, never on the Sale page."),
    "1548292": ("full", ["web_commons::test_categories_levels_load",
                         "web_commons::test_web_filters_color_and_diaper_size",
                         "web_commons::test_web_filters_discounts"],
        "Scenario 2, the mWeb one, is FALCONS-361 step for step: menu > Toys > Explore All, then every "
        "branch of the sub-category filter is walked down a level at a time, the listing and its total "
        "checked at each pick, and the chips cleared before the next. FALCONS-390 adds Color, Diaper "
        "Size and % Discounts applied and cleared on the Diapers category listing. Scenario 1 is "
        "labelled desktop and sits outside the mWeb suite."),
    "1548293": ("none", [],
        "Removed the previous link to test_customer_can_search_brand: that is an APP test and it "
        "is hard-skipped (brand page does not exist on the app). FALCONS-390 filters a search, Sale "
        "and category listing but never a brand page, so this is still not automated."),

    # --- PDP/PLP tax, price, promotions ------------------------------------
    "1018743": ("none", [], "Price and tax display on PLP/PDP/search is never asserted."),
    "1018744": ("partial", ["web_commons::test_web_filters_discounts"],
        "Scenario 1 on one listing: FALCONS-390 turns on % Discounts on the Diapers category PLP and "
        "asserts every product shown carries a struck-through was-price above the price paid. The "
        "special price on the PDP and on the search page (scenarios 2 and 3) is not asserted, and "
        "the products are whatever the listing returns rather than one per product type."),

    # --- Registration -------------------------------------------------------
    "2337052": ("full", ["web_uae::test_uae_user_register_from_account_page",
                         "web_ksa::test_ksa_user_register_from_account_page"],
        "Registration from the account-page sign-in popup, UAE and KSA. Dropped test_user_signup, "
        "which is the app equivalent and is credited on app case 1435392."),
    "2337053": ("full", ["web_uae::test_uae_user_register_from_cart_page",
                         "web_ksa::test_ksa_user_register_from_cart_page",
                         "web_uae::test_uae_checkout_with_cart_items_register_a_new_user_and_coupon",
                         "web_ksa::test_ksa_checkout_with_cart_items_register_a_new_user_and_coupon",
                         "web_uae::test_uae_uf2_cart_gift_wrap_wishlist",
                         "web_ksa::test_ksa_uf2_cart_gift_wrap_wishlist"],
        "Registration from the cart / proceed-to-checkout path, UAE and KSA, both as a dedicated "
        "test and inside the guest-to-registered checkout flows."),

    # --- Log in / Logged out -------------------------------------------------
    "2337055": ("full", ["web_uae::test_uae_user_logs_in_from_account_page",
                         "web_ksa::test_ksa_user_logs_in_from_account_page",
                         "web_commons::test_account_invalid_login_combinations"],
        "Login from the account-page sign-in popup, UAE and KSA, plus a parametrised negative test "
        "(FALCONS-338) asserting the banner and per-field errors for each invalid combination."),
    "2337057": ("full", ["web_uae::test_uae_user_logs_in_from_cart_page",
                         "web_ksa::test_ksa_user_logs_in_from_cart_page",
                         "web_uae::test_uae_cart_guest_login_no_coupon_sc",
                         "web_ksa::test_ksa_cart_guest_login_no_coupon_sc"],
        "Login from the cart page, UAE and KSA, including the guest-with-items variant."),
    "2337056": ("full", ["web_uae::test_uae_user_logs_in_from_account_page",
                         "web_ksa::test_ksa_user_logs_in_from_account_page",
                         "web_uae::test_uae_user_logs_in_from_cart_page",
                         "web_ksa::test_ksa_user_logs_in_from_cart_page",
                         "web_uae::test_uae_cart_uf5_checkout_cod_no_coupon",
                         "web_ksa::test_ksa_cart_uf5_checkout_cod_no_coupon"],
        "Newly credited. account.sign_out() is the final step of all four user tests, and UF5 "
        "signs out mid-flow and signs back in. TestMO flags this case NO -- it should be YES."),
    "1018723": ("none", [], "Cross-platform login is not automated."),

    # --- Forgot / reset password ---------------------------------------------
    "2337058": ("none", [], "Forgot-password flow is not automated."),

    # --- My profile ------------------------------------------------------------
    "1018709": ("full", ["web_commons::test_account_existing_user_profile"],
        "FALCONS-338. Signs in, opens Account > My Profile and verifies first name, last name and "
        "email. This is the first mWeb profile test -- the case previously had only an app test "
        "wrongly credited to it."),
    "1018710": ("none", [], "Editing account info is not automated."),
    "1230430": ("none", [], "Delete Account is not automated."),

    # --- Orders ------------------------------------------------------------------
    "1018706": ("none", [], "Empty order list is not automated."),
    "1018707": ("none", [], "Order list for a user with orders is not automated."),
    "1018708": ("full", ["web_uae::test_uae_checkout_cc_and_verify_odp"],
        "Places a CC order then opens the order details page and verifies the details. "
        "TestMO flags this case NO -- it should be YES."),

    # --- My Wishlist (FALCONS-313) --------------------------------------------------
    "1018714": ("full", ["web_uae::test_uae_wishlist_add_all_product_types_new_user",
                         "web_ksa::test_ksa_wishlist_add_all_product_types_new_user",
                         "web_commons::test_wishlist_add_products_from_plps_new_user",
                         "web_commons::test_wishlist_move_all_product_types_to_cart_new_user"],
        "A brand-new user starts with an empty wishlist and adds every product type from the PDP "
        "(FALCONS-313), from every listing -- Category, SRP, Brand and Sale (FALCONS-312) -- then "
        "moves them all to the cart (FALCONS-296). TestMO flags this NO; it should be YES."),
    "1018717": ("partial", [
        "web_commons::test_wishlist_delete_all_product_types",
        "web_commons::test_wishlist_move_all_product_types_to_cart_existing_user",
        "web_commons::test_wishlist_move_all_product_types_to_cart_new_user",
        "web_uae::test_uae_wishlist_add_all_product_types_existing_user",
        "web_ksa::test_ksa_wishlist_add_all_product_types_existing_user"],
        "FALCONS-315 deletes every product type from the Wishlist page by all three routes -- the "
        "per-item remove icon, Select for specific items with the unselected ones verified to "
        "remain, and Select All for the rest -- ending on the empty state. FALCONS-296 also removes "
        "items by moving them to the cart. Scenario 2 of this case, removing an item by tapping the "
        "heart on its PDP, is still not covered."),
    "1018719": ("full", ["web_uae::test_uae_wishlist_add_all_product_types_existing_user",
                         "web_ksa::test_ksa_wishlist_add_all_product_types_existing_user",
                         "web_commons::test_wishlist_add_products_from_plps_existing_user"],
        "An existing user adds simple, configurable, colour-variant, custom, personalised, bundle "
        "and installation products to the wishlist from the PDP, and FALCONS-312 adds them from "
        "every listing as well -- Category, SRP once per product type, Brand and Sale. Covers the "
        "configurable, custom and bundle types this case names. TestMO flags this NO; it should be "
        "YES."),
    # --- Wallet ---------------------------------------------------------------------
    "1018715": ("none", [], "Empty wallet is not automated."),
    "1018716": ("full", ["web_uae::test_uae_checkout_full_sc_and_verify_sc_balance",
                         "web_uae::test_uae_checkout_cc_and_partial_sc_no_coupon",
                         "web_ksa::test_ksa_checkout_cc_and_partial_sc_no_coupon"],
        "Reads the wallet balance, pays the whole order with store credit and re-reads the balance. "
        "Partial-wallet payment is covered by the CC + partial SC tests."),
    "1018718": ("none", [], "Wallet currency conversion across stores is not automated."),

    # --- Address book ------------------------------------------------------------------
    "1018711": ("partial", ["web_uae::test_uae_checkout_with_cart_items_register_a_new_user_and_coupon",
                            "web_ksa::test_ksa_checkout_with_cart_items_register_a_new_user_and_coupon",
                            "web_uae::test_uae_uf2_cart_gift_wrap_wishlist",
                            "web_ksa::test_ksa_uf2_cart_gift_wrap_wishlist"],
        "Scenario 2 (a new user adds an address on the checkout page) is covered by the "
        "guest-to-registered flows. Scenario 1 (adding from the Address Book page) is not: the closest "
        "test, web_commons::test_account_add_new_address_and_set_default from FALCONS-338, needs a "
        "pre-existing address so the set-as-default control renders, so it runs as an existing user "
        "rather than a new one. It is credited on case 1018712 instead."),
    "1018712": ("partial", ["web_commons::test_account_add_new_address_and_set_default",
                            "web_commons::test_account_delivery_addresses"],
        "FALCONS-338. Adds an address from Delivery Addresses, marks it default and verifies exactly "
        "one default remains, then deletes the address it replaced and confirms it is gone from the "
        "Address Book. Not covered: re-verifying every field after creation, and the rule that the "
        "default toggle is inert while editing the default address."),
    "1018713": ("none", [],
        "Removed the previous link to test_uae_checkout_cc_coupon_modal_sheet, which is unrelated. "
        "Setting a default address or editing address fields from checkout is not automated."),

    # --- OTP ----------------------------------------------------------------------------
    "1125847": ("none", [],
        "Profile phone-number OTP is not automated. test_uae_checkout_cc_wrong_otp_no_coupon is the "
        "3-D Secure card OTP, a different flow."),

    # --- Cart, UF flows ---------------------------------------------------------------------
    "2337029": ("full", ["web_uae::test_uae_cart_existing_user_orders_no_coupon_yalla",
                         "web_ksa::test_ksa_cart_existing_user_orders_no_coupon_yalla"],
        "UF1: existing user with orders, Yalla filter on the PLP, Yalla badge on the PDP and Yalla "
        "free shipping on the cart."),
    "2337030": ("full", ["web_uae::test_uae_uf2_cart_gift_wrap_wishlist",
                         "web_ksa::test_ksa_uf2_cart_gift_wrap_wishlist",
                         "web_uae::test_uae_cart_apply_gift_wrap_and_place_order@test_checkout"],
        "UF2: guest adds items, gift wrap on all items, quantity up, signs up at checkout with a new "
        "address, places a CC order. The standalone gift-wrap-and-order test in test_checkout.py backs "
        "the gift-wrap step (the same-named copy in test_cart.py is hard-skipped as a duplicate). "
        "Dropped the app gift-wrap test that was credited here."),
    "2337022": ("full", ["web_uae::test_uae_cart_guest_login_no_coupon_sc",
                         "web_ksa::test_ksa_cart_guest_login_no_coupon_sc"],
        "UF3: guest with items proceeds to checkout, signs in to an existing user with wallet "
        "balance, item is retained, order paid with full store credit. TestMO flags this NO -- it should be YES."),
    "2337031": ("full", ["web_uae::test_uae_cart_add_items_to_cart_as_a_newly_registered_user_and_apply_cashback_coupon",
                         "web_ksa::test_ksa_cart_add_items_to_cart_as_a_newly_registered_user_and_apply_cashback_coupon"],
        "UF4: newly registered user, no wallet, cashback coupon applied on the cart."),
    "2337032": ("full", ["web_uae::test_uae_cart_uf5_checkout_cod_no_coupon",
                         "web_ksa::test_ksa_cart_uf5_checkout_cod_no_coupon"],
        "UF5: items survive sign-out and sign-in, quantities adjusted per product type, COD order placed."),
    "2337033": ("full", ["web_uae::test_uae_checkout_with_cart_items_register_a_new_user_and_coupon",
                         "web_ksa::test_ksa_checkout_with_cart_items_register_a_new_user_and_coupon"],
        "UF6: guest with items registers at checkout, adds an address, applies a coupon and places the order."),
    "2337034": ("full", ["web_uae::test_uae_cart_guest_login_no_coupon_sc",
                         "web_ksa::test_ksa_cart_guest_login_no_coupon_sc"],
        "UF7: guest with items logs into an existing user holding wallet balance and pays with it. "
        "TestMO flags this NO -- it should be YES."),
    "2337023": ("none", [],
        "Removed the previous link to an app partial-removal test. UF-8 needs a product to be set "
        "out of stock in Admin mid-run, which the storefront suite cannot do."),
    "2337024": ("none", [],
        "Removed the previous link to test_ksa_checkout_cod_normal_coupon. UF-9 needs the BE "
        "low-stock threshold configured; the low-stock alert is not automated."),
    "2337025": ("none", [],
        "Removed the previous link to a gift-wrap test -- a free gift is not gift wrap. UF-10 needs "
        "the Free Gift Rule Wizard configured in Admin."),
    "2114394": ("none", [],
        "Removed the previous link to test_ksa_cart_apply_gift_wrap_and_place_order. Apple Pay is "
        "not automated on any platform."),
    "2114395": ("none", [], "Apple Pay is not automated."),
    "2337026": ("none", [], "Free gift UI needs the Free Gift Rule Wizard configured; not automated."),

    # --- Checkout ---------------------------------------------------------------------------------
    "2337037": ("full", ["web_uae::test_uae_checkout_cc_no_coupon",
                         "web_ksa::test_ksa_checkout_cc_no_coupon",
                         "web_uae::test_uae_checkout_cc_normal_coupon",
                         "web_uae::test_uae_checkout_cc_coupon_modal_sheet",
                         "web_ksa::test_ksa_checkout_cc_normal_coupon"],
        "CC checkout, parametrised across simple / bundle / configurable / custom on UAE, plus KSA "
        "and the coupon variants. The KSA + normal coupon test is currently hard-skipped as flaky."),
    "2337038": ("full", ["web_uae::test_uae_checkout_cc_and_partial_sc_no_coupon",
                         "web_ksa::test_ksa_checkout_cc_and_partial_sc_no_coupon",
                         "web_uae::test_uae_cart_partial_sc_and_checkout_with_cc"],
        "CC plus partial store credit, applied both at checkout and on the cart (FALCONS-268)."),
    "2337039": ("full", ["web_uae::test_uae_checkout_cod_no_coupon",
                         "web_ksa::test_ksa_checkout_cod_no_coupon",
                         "web_uae::test_uae_checkout_cod_normal_coupon",
                         "web_uae::test_uae_percentage_of_product_price_discount_rules_with_max_amount",
                         "web_ksa::test_ksa_percentage_of_product_price_discount_rules_with_max_amount",
                         "web_ksa::test_ksa_checkout_cod_normal_coupon"],
        "COD checkout parametrised by product type, plus COD with a coupon and COD with a "
        "capped percentage cart rule. The KSA COD + coupon test is currently hard-skipped as flaky."),
    "2337040": ("full", ["web_uae::test_uae_checkout_full_sc_no_coupon",
                         "web_ksa::test_ksa_checkout_full_sc_no_coupon",
                         "web_uae::test_uae_cart_full_sc_and_checkout"],
        "Full store credit brings the order total to zero and the order is placed without a card."),
    "2337041": ("full", ["web_uae::test_uae_checkout_invalid_cc_no_coupon",
                         "web_ksa::test_ksa_checkout_invalid_cc_no_coupon",
                         "web_uae::test_uae_checkout_cc_wrong_otp_no_coupon",
                         "web_ksa::test_ksa_checkout_cc_wrong_otp_no_coupon"],
        "Invalid card and wrong 3-D Secure OTP, both stores, error message asserted."),
    "2337042": ("full", ["web_uae::test_uae_checkout_full_sc_and_normal_coupon",
                         "web_uae::test_uae_checkout_cc_partial_sc_and_normal_coupon",
                         "web_ksa::test_ksa_checkout_full_sc_and_normal_coupon",
                         "web_ksa::test_ksa_checkout_cc_partial_sc_and_normal_coupon"],
        "Store credit and a coupon applied together, both full-SC and partial-SC + CC, both stores."),
    "2337043": ("full", ["web_uae::test_uae_checkout_tamara_no_coupon",
                         "web_uae::test_uae_checkout_tamara_normal_coupon",
                         "web_uae::test_uae_checkout_tamara_cashback_coupon",
                         "web_ksa::test_ksa_checkout_tamara_no_coupon",
                         "web_ksa::test_ksa_checkout_tamara_normal_coupon",
                         "web_ksa::test_ksa_checkout_tamara_cashback_coupon"],
        "Tamara with no coupon, a normal coupon and a cashback coupon, both stores. Dropped the app "
        "Tamara test that was credited here -- it is app-side and hard-skipped. "
        "TestMO flags this NO -- it should be YES."),
    "2337044": ("full", ["web_uae::test_uae_checkout_tabby_no_coupon",
                         "web_uae::test_uae_checkout_tabby_normal_coupon",
                         "web_uae::test_uae_checkout_tabby_cashback_coupon",
                         "web_ksa::test_ksa_checkout_tabby_no_coupon",
                         "web_ksa::test_ksa_checkout_tabby_normal_coupon",
                         "web_ksa::test_ksa_checkout_tabby_cashback_coupon"],
        "Tabby with no coupon, a normal coupon and a cashback coupon, both stores. "
        "TestMO flags this NO -- it should be YES."),
    "2337036": ("none", [],
        "Removed the previous link to test_uae_checkout_cod_normal_coupon. Apple Pay is not automated."),
    "2337045": ("none", [],
        "Removed the previous link to test_ksa_checkout_invalid_cc_no_coupon, which has nothing to "
        "do with the exit prompt. TestMO flags this case YES -- the flag is wrong, nothing covers it."),
    "2283422": ("none", [],
        "This case starts from an order created in Admin. The storefront ODP verification we do have "
        "(test_uae_checkout_cc_and_verify_odp) is credited on case 1018708; Admin and invoice checks "
        "are not automated."),

    # --- Coupon -----------------------------------------------------------------------------------------
    "1018758": ("partial", [
        "web_uae::test_uae_checkout_cc_normal_coupon",
        "web_uae::test_uae_checkout_cc_coupon_modal_sheet",
        "web_uae::test_uae_cart_remove_item_with_applied_coupon",
        "web_ksa::test_ksa_cart_remove_item_with_applied_coupon",
        "web_uae::test_uae_new_user_cart_remove_item_with_applied_coupon",
        "web_ksa::test_ksa_new_user_cart_remove_item_with_applied_coupon"],
        "Applying a coupon on the cart and at checkout is covered, through the coupon modal sheet "
        "too, and FALCONS-294 added KSA and new-user twins of the remove-item-with-coupon "
        "recalculation. The point of this case -- that a single-use coupon is refused on a second "
        "use by the same or another customer -- is still not asserted."),
    "1018759": ("full", [
        "web_uae::test_uae_percentage_of_product_price_discount_rules_without_max_amount",
        "web_uae::test_uae_percentage_of_product_price_discount_rules_with_max_amount",
        "web_ksa::test_ksa_percentage_of_product_price_discount_rules_without_max_amount",
        "web_ksa::test_ksa_percentage_of_product_price_discount_rules_with_max_amount",
        "web_uae::test_uae_new_user_percentage_of_product_price_discount_rules_without_max_amount",
        "web_ksa::test_ksa_new_user_percentage_of_product_price_discount_rules_without_max_amount"],
        "Percentage-of-product-price rule with and without a max discount amount, both storefronts, "
        "order summary verified and the order placed. FALCONS-294 added new-user twins, so the rule "
        "is proven for a first-time customer as well as an existing one."),
    "1018760": ("full", [
        "web_uae::test_uae_percentage_of_product_variant_price_discount_rules_with_max_amount",
        "web_uae::test_uae_percentage_of_product_variant_price_discount_rules_without_max_amount",
        "web_ksa::test_ksa_percentage_of_product_variant_price_discount_rules_with_max_amount",
        "web_ksa::test_ksa_percentage_of_product_variant_price_discount_rules_without_max_amount",
        "web_uae::test_uae_new_user_percentage_of_product_variant_price_discount_rules_with_max_amount",
        "web_uae::test_uae_new_user_percentage_of_product_variant_price_discount_rules_without_max_amount",
        "web_ksa::test_ksa_new_user_percentage_of_product_variant_price_discount_rules_with_max_amount",
        "web_ksa::test_ksa_new_user_percentage_of_product_variant_price_discount_rules_without_max_amount"],
        "Percentage rule on product variants, sale and non-sale in the same cart, with and without "
        "a max amount, both storefronts, paid by COD and by card. FALCONS-294 added a new-user twin "
        "of each."),
    "1018761": ("full", ["web_uae::test_uae_bank_discount_percentage_of_product_price_rule",
                         "web_ksa::test_ksa_bank_discount_percentage_of_product_price_rule"],
        "Bank coupon viewed on the cart, re-checked after a quantity change, applied, order summary "
        "verified and a CC order placed. Both tests are skipif OS == ios, so this runs on Android/Chrome only."),
    "1018762": ("none", [],
        "Removed the previous link to a KSA percentage test -- wrong rule type. The fixed-amount "
        "coupons (FF_15 / FW_20) this case is about are not automated."),
    "1084824": ("full", [
        "web_uae::test_uae_tiered_coupon_steps_up_and_caps",
        "web_uae::test_uae_uncapped_tiered_coupon_keeps_increasing",
        "web_uae::test_uae_new_user_tiered_coupon_steps_up_and_caps",
        "web_uae::test_uae_new_user_uncapped_tiered_coupon_keeps_increasing",
        "web_ksa::test_ksa_tiered_coupon_steps_up_and_caps",
        "web_ksa::test_ksa_uncapped_tiered_coupon_keeps_increasing",
        "web_ksa::test_ksa_new_user_tiered_coupon_steps_up_and_caps",
        "web_ksa::test_ksa_new_user_uncapped_tiered_coupon_keeps_increasing"],
        "FALCONS-364 covers both scenarios of the rule, on both storefronts. Scenario 1 "
        "(tierednomax): the uncapped test proves the coupon is refused below the cost step, then that "
        "the discount keeps growing as the quantity rises. Scenario 2 (tieredmax): the capped test "
        "walks the subtotal up through the steps and verifies the discount stops at its cap and holds "
        "there. Both reconcile VAT and the order total and place a credit-card order; each has a new- "
        "user twin."),
    # --- Gift Registry (FALCONS-339) -----------------------------------------------------------------------
    "2337059": ("full", ["web_commons::test_gift_registry_create_from_my_account",
                         "web_commons::test_gift_registry_create_from_pdp"],
        "Both scenarios now covered. Scenario 1: My Account > Gift registry, pick an occasion, name "
        "it, submit, verify the detail page and the listing. Scenario 2 (FALCONS-340): a guest taps "
        "Add to Registry on a PDP, is sent to sign-in, signs in and creates the registry from the "
        "Add to Registry sheet on the same PDP."),
    "2337061": ("full", ["web_commons::test_gift_registry_order_from_share_link"],
        "FALCONS-341. The owner builds a registry with every product type and publishes it -- event "
        "date, location, gift delivery address, visibility -- then the share link is captured and "
        "proven to work by a second user opening it. That is the whole setup flow this case describes."),
    "2337060": ("full", ["web_commons::test_gift_registry_create_from_pdp"],
        "FALCONS-340. The case asks that a customer with a registry can add a product from the PDP to "
        "it; the test does that for every product type and verifies each one landed. Complete per the "
        "QA owner (8 Sep 2026) -- the quantity and delete actions in the steps field exercise the "
        "registry screen rather than the add-from-PDP behaviour the case is about."),
    "2337062": ("full", ["web_commons::test_gift_registry_order_from_share_link"],
        "FALCONS-341 covers scenario 1 exactly: the buyer signs in with an empty cart, adds an item "
        "of their own, opens the owner's share link and adds every registry product. The cart then "
        "shows two groups and the registry group is asserted to hold all of them."),
    "2337063": ("full", ["web_commons::test_gift_registry_order_from_share_link"],
        "FALCONS-341. The buyer switches the cart to the registry group, checks out that group alone "
        "and pays by credit card. Replaces the old link to test_ksa_checkout_cc_normal_coupon, which "
        "was unrelated and hard-skipped."),
    "1018774": ("partial", ["web_commons::test_gift_registry_purchase_shows_for_owner"],
        "The owner builds and publishes a registry, a buyer orders from the share link and pays by "
        "card, then the owner signs back in and the order is found under the registry's Purchased "
        "tab. Scenario 2 of this case -- that an item's desired quantity drops once purchased -- is "
        "not asserted."),
}

# Every "Verify adding X item from Admin" case -- Admin-side product creation is
# outside what a storefront E2E suite can do.
for _case in ("2439692", "2439693", "2439694", "2439695", "2439696", "2439697",
              "2439698", "2439699", "2439821", "2439822", "2439823"):
    WEB_MAPPING[_case] = ("none", [], "Admin-side product creation is out of scope for the storefront E2E suite.")

# Remaining catalogue / geo cases with nothing to say beyond "not automated".
for _case, _why in (
    ("1018731", "Geo-IP country and city detection is not automated."),
    ("1018732", "Geo-IP detection with multiple saved addresses is not automated."),
    ("1018733", "Geo-IP detection for guests is not automated."),
    ("1018736", "Switching country / website is not automated."),
    ("1018735", "Switching currency is not automated."),
):
    WEB_MAPPING[_case] = ("none", [], _why)


# --------------------------------------------------------------------------
# Native app -- release checklist, TestMO repository 241
# --------------------------------------------------------------------------
APP_MAPPING = {
    "1435389": ("full", ["app::test_app_explore_screen_elements_and_navigate_to_account"],
        "Verifies the explore feed, search header and bottom navigation load, then navigates to "
        "Account. TestMO flags this Not planned even though it is automated."),
    "1435417": ("none", [], "Home-page banners are not asserted."),
    "1435425": ("partial", ["app::test_customer_can_search_product_in_specific_category"],
        "Reaches the category PLP through a search suggestion rather than the home-page category "
        "entry point, and only on the configured store -- UAE/KSA/GCC/International are not each "
        "covered. Now hard-skipped on main: the new Algolia search no longer returns category "
        "suggestions, so the flow this script drives no longer exists."),
    "1435426": ("none", [], "Collections from the home page are not automated."),
    "1435390": ("full", ["app::test_app_category_levels_as_guest",
                         "app::test_app_category_levels_as_signed_in_user"],
        "FALCONS-361. From the Categories tab: the L1 list loads, Toys opens its L2 list, a "
        "sub-category with children opens its PLP, then every chip is selected in turn and descended "
        "until the listing stops narrowing -- each reload verified. Run as a guest and as a "
        "signed-in user."),
    "1435404": ("full", ["app::test_app_filters_on_sale_category_listing",
                         "app::test_app_filters_discounts",
                         "app::test_app_filters_price_slider",
                         "app::test_app_filters_one_filter_at_a_time",
                         "app::test_app_filters_multiple_filters_from_sheet",
                         "app::test_app_filters_yalla_from_listing",
                         "app::test_app_filters_from_both_entry_points",
                         "app::test_app_sort_by_price_from_both_entry_points"],
        "FALCONS-388. Filters on category listings: Category, Colour, Diaper Size and Shoe Size on "
        "the Sale listing, the price slider there with every price checked against the ceiling, and "
        "Discounts on a sub-category listing with every card showing a was-price. The rest of the "
        "suite applies, stacks and clears Age, Gender, Category, Brand and Yalla from both the top "
        "row and the floating bar, and sorts by price both ways with the order verified. Sort runs "
        "on a listing opened from search -- the same PLP screen and controls."),
    "1435391": ("partial", ["app::test_app_gift_registry_create_from_pdp_all_product_types"],
        "Opens the PDP for simple, bundle, configurable, custom, custom-configurable and "
        "installation products and selects their options, but as part of the gift-registry flow -- "
        "the PDP content itself is not asserted. Colour variant and egift are not covered."),
    "2884189": ("none", [], "Submitting a review is not automated."),
    "2884190": ("none", [], "Reviews and ratings on the PDP are not automated."),
    "1435418": ("partial", ["app::test_app_gift_registry_create_from_pdp_all_product_types",
                            "app::test_app_gift_registry_create_from_pdp"],
        "Newly credited (FALCONS-282). Adds a product to a registry from the PDP for six product "
        "types and verifies the event name, product name and quantity on the registry detail screen. "
        "Colour variant and egift are not covered."),
    "1435416": ("full", ["app::test_customer_can_search_brand"],
        "Now automated: the script that was hard-skipped because the app had no brand page is live "
        "again on main, opening the brand page from a search suggestion. Still flagged Not planned "
        "in TestMO, so it sits outside the percentages until that changes."),
    "2885050": ("none", [],
        "Brand-page product loading with filter and sort is not automated. FALCONS-388 filters and "
        "sorts search and category listings only; test_customer_can_search_brand opens a brand page "
        "but neither filters nor sorts it."),
    "2885052": ("full", ["app::test_existing_user_profile",
                         "app::test_app_invalid_login_combinations"],
        "Positive sign-in through the bottom sheet, plus a parametrised negative test asserting the "
        "banner and per-field errors for every invalid email / password combination."),
    "2885053": ("partial", ["app::test_sign_in_with_google"],
        "Script exists but is hard-skipped: Google sign-in requires 2-factor authentication."),
    "1435392": ("full", ["app::test_user_signup", "app::test_app_uf2_cart_gift_wrap_wishlist"],
        "Dedicated signup test, plus signup as part of the guest checkout flow. "
        "TestMO flags this NO -- it should be YES."),
    "2885051": ("none", [], "Adding products from Algolia recommendations is not automated."),
    "1435401": ("full", ["app::test_app_add_all_product_types_from_srp",
                            "app::test_app_cart_add_all_product_type_variants_and_verify",
                            "app::test_uae_cart_bundle_multiple_variants",
                            "app::test_uae_cart_configurable_multiple_variants"],
        "Search results page and PLP add-to-cart are covered for simple, custom, configurable and "
        "bundle, including the \"Select an option\" popup; PDP option selection is covered for bundle "
        "and configurable. Complete per the QA owner (8 Sep 2026): the brand entry point and the "
        "remaining product types in the case title are not applicable to app automation. Dropped "
        "the hard-skipped test_uae_cart_quantity_workflow."),
    "1435405": ("full", ["app::test_app_cart_add_all_product_type_variants_and_verify",
                            "app::test_app_add_all_product_types_from_srp"],
        "Every added product is verified by name in the cart, for simple, custom, configurable and "
        "bundle. Complete per the QA owner (8 Sep 2026): the remaining product types in the "
        "case title are not applicable to app automation. Dropped the hard-skipped "
        "test_uae_cart_quantity_workflow."),
    "1435406": ("full", ["app::test_uae_cart_increase_and_decrease_quantity",
                            "app::test_uae_cart_item_integrity_after_quantity_change"],
        "Quantity up and down with the row re-verified after each step, parametrised over simple, "
        "bundle, configurable and custom. Complete per the QA owner (8 Sep 2026): the remaining "
        "product types in the case title are not applicable to app automation. Note these are the "
        "APP copies; identically-named web tests exist in tests/web/UAE/test_cart.py."),
    "1435407": ("full", ["app::test_uae_cart_remove_item",
                            "app::test_app_uae_cart_remaining_items_unaffected_after_partial_removal",
                            "app::test_app_uae_cart_order_summary_updates_after_item_removal"],
        "Removal is proven, including that the remaining items and the order summary are correct "
        "afterwards. Complete per the QA owner (8 Sep 2026): a per-product-type sweep is not required here."),
    "1435408": ("full", ["app::test_uae_checkout_apply_gift_wrap_place_order",
                         "app::test_app_uf2_cart_gift_wrap_wishlist"],
        "Gift wrap added on the cart and the order placed with CC. Dropped "
        "test_app_cart_apply_gift_wrap_and_place_order, hard-skipped because it moved to the "
        "checkout suite. TestMO flags this NO -- it should be YES."),
    "1435409": ("full", [
        "app::test_app_uae_cart_remove_item_with_applied_coupon",
        "app::test_app_new_user_cart_remove_item_with_applied_coupon",
        "app::test_app_percentage_of_product_price_discount_rules_with_max_amount",
        "app::test_app_percentage_of_product_price_discount_rules_without_max_amount",
        "app::test_app_new_user_percentage_of_product_price_discount_rules_without_max_amount",
        "app::test_app_percentage_of_product_variant_price_discount_rules_with_max_amount",
        "app::test_app_percentage_of_product_variant_price_discount_rules_without_max_amount",
        "app::test_app_new_user_percentage_of_product_variant_price_discount_rules_with_max_amount",
        "app::test_app_new_user_percentage_of_product_variant_price_discount_rules_without_max_amount",
        "app::test_app_bank_discount_percentage_of_product_price_rule",
        "app::test_app_tiered_coupon_steps_up_and_caps",
        "app::test_app_uncapped_tiered_coupon_keeps_increasing",
        "app::test_app_new_user_tiered_coupon_steps_up_and_caps",
        "app::test_app_new_user_uncapped_tiered_coupon_keeps_increasing"],
        "FALCONS-342 closed the gap: the capped percentage test applies a coupon on the cart, REMOVES "
        "it there, verifies the checkout summary loses the discount, then re-applies it on checkout "
        "-- so apply and remove are both proven. Every cart-price-rule variant is covered, "
        "FALCONS-294 added new-user twins of each, the bank-coupon test is live on main again, and "
        "FALCONS-364 added the tiered rule, capped and uncapped, with its own new-user twins."),
    "1435393": ("full", ["app::test_existing_user_profile"],
        "Signs in and verifies every detail on the My Profile screen. TestMO flags this NO -- it should be YES."),
    "1435394": ("none", [], "There is no app order-list / order-details test."),
    "1435395": ("none", [],
        "Not automated. This case is a standalone check that the wishlist screen loads for an "
        "existing customer. test_app_wishlist_all_product_types does open the wishlist, but only as "
        "a step inside a cart-to-wishlist flow, so it does not stand in for this case (QA owner, "
        "8 Sep 2026). That test is credited on 1435396 and 1435397 instead."),
    "1435396": ("full", [
        "app::test_app_wishlist_all_product_types",
        "app::test_app_wishlist_from_pdp",
        "app::test_app_wishlist_from_pdp_new_user",
        "app::test_app_wishlist_add_products_from_plps",
        "app::test_app_wishlist_guest_add_from_plp_prompts_login",
        "app::test_app_wishlist_guest_add_from_pdp_prompts_login"],
        "All three entry points are covered, now for every product type rather than a single "
        "product. Cart: all seven types moved to the wishlist, including the guest login-prompt "
        "branch. PDP (FALCONS-295): adds from the PDP for an existing user and a new one. PLP "
        "(FALCONS-312): adds from every listing, plus the guest flows where the heart opens the "
        "sign-in sheet first."),
    "1435397": ("full", [
        "app::test_app_wishlist_all_product_types",
        "app::test_app_wishlist_delete_all_product_types"],
        "FALCONS-315 deletes every product type by all three routes the app offers -- the per-item "
        "trash icon, Select for specific items, and Select All -- finishing on the empty state. The "
        "wishlist flow test also clears the list by bulk selection as a precondition and asserts it "
        "empties."),
    "1435398": ("none", [], "The app wallet page is not automated."),
    "1435400": ("partial", ["app::test_add_new_address_and_make_default_and_delete",
                            "app::test_existing_user_delivery_address"],
        "Adds an address, sets it as default, moves the default to another address, deletes one and "
        "verifies the remaining count. Editing an existing address is not covered."),
    "1435402": ("full", ["app::test_app_add_all_product_types_from_srp",
                         "app::test_app_sort_by_price_from_both_entry_points"],
        "Search from the explore screen to the full search results page, where every product type is "
        "found and added; the FALCONS-388 suite opens its listing the same way. Dropped "
        "test_customer_can_search_product_in_specific_category, now hard-skipped because the new "
        "Algolia search no longer offers category suggestions. TestMO flags this NO -- it should be YES."),
    "1435403": ("full", ["app::test_app_filters_one_filter_at_a_time",
                         "app::test_app_filters_multiple_filters_from_sheet",
                         "app::test_app_filters_yalla_from_listing",
                         "app::test_app_filters_from_both_entry_points",
                         "app::test_app_sort_by_price_from_both_entry_points"],
        "FALCONS-388, all on a search results listing. Age, Gender, Category and Brand each applied "
        "and cleared, the count matching the sheet's 'Show N Results'; the same facets stacked one "
        "after another; Yalla applied from the listing with every product checked; a filter applied "
        "from the top row and from the floating bar; and price sort low-to-high then high-to-low "
        "with the order verified."),
    "1543903": ("full", ["app::test_app_cart_partial_sc_and_checkout_with_cc",
                         "app::test_app_cart_full_sc_and_checkout"],
        "FALCONS-268. Both tests apply store credit on the cart, verify it, remove it, verify the "
        "totals recover, re-apply it and then check out -- partial SC paid off with CC, and full SC "
        "covering the whole order. Replaces the unrelated order-summary test that was credited here."),
    "1543904": ("full", ["app::test_app_uae_cart_order_summary_updates_after_item_removal",
                         "app::test_app_cart_partial_sc_and_checkout_with_cc",
                         "app::test_app_cart_full_sc_and_checkout"],
        "Captures subtotal, discount, VAT and total on the cart and re-verifies them after an item is "
        "removed; the SC tests validate the order summary again after each apply and remove. Replaces "
        "the previous link to the hard-skipped test_app_cart_guest_login_no_coupon_sc."),
    "1543905": ("partial", ["app::test_uae_guest_checkout_login_bottom_sheet_and_place_order",
                            "app::test_app_uf2_cart_gift_wrap_wishlist"],
        "The address is handled during checkout (selected, or added at signup), but the shipping "
        "address block on the checkout screen is never asserted. Dropped test_app_checkout_tabby_normal_coupon, "
        "which has nothing to do with addresses."),
    "1543906": ("partial", ["app::test_uae_checkout_cc_no_coupon",
                            "app::test_uae_checkout_cod_no_coupon",
                            "app::test_app_checkout_full_sc_no_coupon",
                            "app::test_uae_checkout_cc_and__no_coupon",
                            "app::test_uae_checkout_tabby_no_coupon",
                            "app::test_app_cart_uf5_checkout_cod_no_coupon"],
        "CC, COD, full store credit, CC + SC and Tabby are each selected on the checkout screen and "
        "paid. Apple Pay is not automated and both Tamara scripts are hard-skipped as flaky, so the "
        "full payment-method list is not verified."),
    "1543907": ("full", ["app::test_uae_checkout_cc_no_coupon",
                            "app::test_uae_checkout_tabby_no_coupon",
                            "app::test_app_checkout_tabby_cashback_coupon",
                            "app::test_app_checkout_tabby_normal_coupon",
                            "app::test_app_uae_checkout_tamara_no_coupon",
                            "app::test_app_checkout_tamara_normal_coupon"],
        "CC and Tabby orders are placed end to end. Apple Pay is excluded as not automatable -- it "
        "requires device biometric confirmation -- so it does not count against this case (QA owner, "
        "8 Sep 2026). Two residuals tracked separately: both Tamara scripts are hard-skipped as "
        "flaky, and the ODP / Admin / invoice checks named in the case title are not verified on "
        "the app. Removed the web CC and Tabby tests that were wrongly credited here."),
    "1435419": ("full", ["app::test_app_gift_registry_order_from_share_link",
                         "app::test_app_gift_registry_scenario_4_add_to_cart_via_deeplink"],
        "FALCONS-355. A per-product-type owner builds a registry from the PDP, the share link is "
        "copied, a brand-new buyer adds the registry product to their cart alongside one of their "
        "own, and pays by card. The older deep-link script is still hard-skipped pending an app- "
        "side fix and carries the AE-only marker; the new share-link test does not, so this case "
        "runs on SA too."),
    "1435420": ("full", ["app::test_app_gift_registry_order_from_share_link",
                         "app::test_app_gift_registry_scenario_4_add_to_cart_via_deeplink"],
        "FALCONS-355 covers the multiple-cart case directly: the buyer holds their own product and "
        "the registry's, the registry item is verified under its own cart switch, the registry "
        "group is paid for, and the buyer's own product is then checked to be untouched by that "
        "order. The owner's Purchased tab is verified too. The new share-link test is not AE-gated, unlike the rest of that file, so this case runs on SA as well."),
    "1543957": ("full", ["app::test_uae_guest_checkout_login_bottom_sheet_and_place_order",
                         "app::test_app_cart_guest_login_no_coupon_sc"],
        "A guest adds an item, taps checkout, signs in through the login bottom sheet and the item "
        "is still in the cart; parametrised by product type. The iOS gate this case used to carry "
        "has been removed on main. The store- "
        "credit variant of the same flow is unskipped on main again."),
    "1543908": ("none", [], "Algolia recommendations across screens are not automated."),
    "1435415": ("none", [], "App close / reopen is not automated."),
    "1543946": ("none", [],
        "External, email and banner deep links are not automated. The only deep-link script is the "
        "gift-registry one, which is registry-specific and hard-skipped."),
    "1543948": ("none", [], "Push and in-app notifications are not automated."),
    "2282943": ("none", [], "Push notifications with the app killed are not automated."),
    "2282944": ("none", [], "Push notifications with the app backgrounded are not automated."),
    "2673949": ("none", [], "Maya navigation to the PDP is not automated."),
    "2673950": ("none", [], "Maya add-to-cart is not automated."),
    "2673956": ("none", [], "GTM event verification is not automated."),
}

# Tests that guard real behaviour for which no TestMO case exists.
#
# FALCONS-336 ported 12 cart scenarios from the app suite to mWeb. They run and
# pass, but the mWeb regression repository (group 73697) describes the cart only
# as the UF1-UF12 user flows -- it has no granular cart-behaviour cases. So these
# tests cannot raise mWeb's case coverage until TestMO has cases for them.
#
# Each entry names the app case that already describes the same behaviour, so the
# mWeb case can be written by mirroring it.
PLAN_GAPS = {
    "web_uae::test_uae_cart_remove_item":
        ("1435407", "Verify user can remove products from cart - All product types"),
    "web_uae::test_uae_cart_remaining_items_unaffected_after_partial_removal":
        ("1435407", "Verify user can remove products from cart - All product types"),
    "web_uae::test_uae_cart_order_summary_updates_after_item_removal":
        ("1543904", "Verify order summary in cart"),
    "web_uae::test_uae_cart_increase_and_decrease_quantity":
        ("1435406", "Verify user can update product qty on cart - All product types"),
    "web_uae::test_uae_cart_item_integrity_after_quantity_change":
        ("1435406", "Verify user can update product qty on cart - All product types"),
    "web_uae::test_uae_cart_bundle_multiple_variants":
        ("1435405", "Verify product list in cart - All product types"),
    "web_uae::test_uae_cart_configurable_multiple_variants":
        ("1435405", "Verify product list in cart - All product types"),
    "web_uae::test_uae_cart_add_all_product_types_and_verify":
        ("1435401", "Verify user can add all product types from PLP, search, brand, PDP"),
    "app::test_app_cart_existing_user_orders_no_coupon_yalla":
        ("2337029", "UF1 - Yalla free shipping on the cart (mWEB case; no app equivalent)"),
    "app::test_app_gift_registry_create_from_my_registries":
        ("2337059", "Gift Registry creation from My account (mWEB case; no app equivalent)"),
    "web_commons::test_home_screen_elements_and_navigate_to_account":
        ("1435389", "Verify home page is loading (app case; the mWEB set has no home-page case)"),
    "web_commons::test_home_search_product_in_specific_category":
        ("1435425", "Categories from home page (app case; the mWEB set has no equivalent)"),
    "web_uae::test_uae_wishlist_guest_add_prompts_login":
        ("1018714", "Wishlist cases cover new/existing users; none covers the guest login prompt"),
    "web_ksa::test_ksa_wishlist_guest_add_prompts_login":
        ("1018714", "Wishlist cases cover new/existing users; none covers the guest login prompt"),
    # An automatic promotion that discounts the cart with no coupon entered.
    # Every Coupon case in the plan starts with "apply coupon on cart", so none
    # of them describes a rule that needs no code at all.
    "web_uae::test_uae_auto_discount_applied_without_coupon":
        ("", "Automatic cart discount with no coupon entered -- the Coupon cases all assume a code"),
    "web_uae::test_uae_new_user_auto_discount_applied_without_coupon":
        ("", "Automatic cart discount, new user -- the Coupon cases all assume a code"),
    "web_ksa::test_ksa_auto_discount_applied_without_coupon":
        ("", "Automatic cart discount with no coupon entered -- the Coupon cases all assume a code"),
    "web_ksa::test_ksa_new_user_auto_discount_applied_without_coupon":
        ("", "Automatic cart discount, new user -- the Coupon cases all assume a code"),
    "app::test_app_auto_discount_applied_without_coupon":
        ("", "Automatic cart discount with no coupon entered -- no app case describes it"),
    "app::test_app_new_user_auto_discount_applied_without_coupon":
        ("", "Automatic cart discount, new user -- no app case describes it"),
    # FALCONS-383 / FALCONS-384 -- coupons restricted to a brand or a category.
    # The Coupon cases cover percentage, variant, bank, fixed and tiered rules;
    # none describes a rule scoped to a brand or category.
    **{ref: ("", "Brand restricted coupon -- no Coupon case describes a brand-scoped rule")
       for ref in ("web_uae::test_uae_brand_restricted_coupon_discount",
                   "web_uae::test_uae_new_user_brand_restricted_coupon_discount",
                   "web_ksa::test_ksa_brand_restricted_coupon_discount",
                   "web_ksa::test_ksa_new_user_brand_restricted_coupon_discount",
                   "app::test_app_brand_restricted_coupon_discount",
                   "app::test_app_new_user_brand_restricted_coupon_discount")},
    **{ref: ("", "Category restricted coupon -- no Coupon case describes a category-scoped rule")
       for ref in ("web_uae::test_uae_category_restricted_coupon_discount",
                   "web_uae::test_uae_new_user_category_restricted_coupon_discount",
                   "web_ksa::test_ksa_category_restricted_coupon_discount",
                   "web_ksa::test_ksa_new_user_category_restricted_coupon_discount",
                   "app::test_app_category_restricted_coupon_discount",
                   "app::test_app_new_user_category_restricted_coupon_discount")},
    # FALCONS-347/348/349 -- the Now vertical. A new product area; neither TestMO
    # export carries cases for it, so none of this can raise a percentage yet.
    "app::test_super_app_vertical_switcher_only_in_uae":
        ("", "Now vertical availability -- no TestMO case exists for the Now vertical"),
    "app::test_super_app_now_serviceable_address_restores_availability":
        ("", "Now vertical serviceability -- no TestMO case exists for the Now vertical"),
    "app::test_super_app_now_non_serviceable_address_validation":
        ("", "Now vertical serviceability -- no TestMO case exists for the Now vertical"),
    "app::test_super_app_now_guest_shop_coupon_login_and_place_cc_order":
        ("", "Now vertical guest order journey -- no TestMO case exists for the Now vertical"),
    "app::test_superapp_new_user_end_to_end_journey":
        ("", "Now vertical new-user journey -- no TestMO case exists for the Now vertical"),
    "app::test_uae_checkout_invalid_cc_no_coupon":
        ("2337041", "Checkout - Invalid transactions (mWEB case; the app checklist has no equivalent)"),
}

ARABIC = {
    "summary": ("Arabic is a run dimension, not a separate set of cases: the same suites run with "
                "LOCALE=en and LOCALE=ar, so the case counts below are unchanged."),
    # Said plainly, because the distinction matters when this is presented.
    "caveat": ("AR-safe covers two designs: suites carrying locale-aware locators and data "
               "(FALCONS-321/330/335/336), and suites written locale-agnostic -- asserting whatever "
               "the UI rendered rather than an English string, so they need no per-locale data at "
               "all. Neither is a passing Arabic run: as of the 31 Aug review the Arabic suite had "
               "not been executed on BrowserStack on either platform, so every pass rate quoted "
               "anywhere is an English run."),
    "tickets": [
        {"id": "FALCONS-321", "pr": 224, "what": "Arabic locale support for the native app, plus Android/iOS optimisations"},
        {"id": "FALCONS-330", "pr": 228, "what": "Arabic locale support for mWeb, plus iOS Safari CC coverage"},
        {"id": "FALCONS-335", "pr": 239, "what": "mWeb UAE cart and user suites stabilised in EN and AR"},
        {"id": "FALCONS-336", "pr": None, "what": "Locale-aware cart wishlist title and quantity alert; products that resolve to one slug in both locales"},
    ],
    "stores": ["/ar (AE)", "/sa-ar", "/bh-ar", "/kw-ar", "/global-ar"],
    "app_locale_selectors": 233,
    "language_data_keys": ["categories.all", "coupons.unlock_bank_coupon_msg",
                           "address.ae", "address.sa", "sign_in_errors"],
    "mechanics": [
        "tests/conftest.py maps (COUNTRY, LOCALE) to the store URL suffix and fails fast on an invalid pair",
        "get_selector() resolves locale-nested locators with an 'en' fallback",
        "pagesApp/HomePage.py::select_locale() picks العربية or English on the app locale picker",
        "tests/app/test_app_account.py carries AR area names and AR sign-in error strings",
    ],
}


def _source_dates():
    """When each TestMO export was actually taken.

    generated_at says when the report was last built, and CI rebuilds daily --
    so it stays green no matter how old the case data is. These are the dates
    that matter for "is the case list current?".
    """
    import datetime
    out = {}
    for key, name in (("mweb_release_run", "testmo_tests.json"),
                      ("app_release_checklist", "app_testmo_tests.json"),
                      ("mweb_regression_repo", "web_regression_tests.json")):
        path = HERE / name
        if path.exists():
            src = json.loads(path.read_text())
            d = src[0].get("_exported") if src and isinstance(src[0], dict) else None
            out[key] = d or "unknown"
    return out


def _case_links():
    """case_id -> how to open that case in TestMO.

    Two forms, in order of preference:

    * `run` + `test_id` -> /runs/view/{run}?test_id={id} opens the case
      directly, no pagination involved. Test ids come from the run exports
      (2154 for mWEB, 2192 for app); a repository export has no Test ID column.
    * `page` -> the repository listing paginates, so a link without the page
      number lands on page 1 with the case nowhere in sight. The page depends on
      a case's position in the unfiltered listing, which no export gives us, so
      these values are carried rather than computed.

    A case with neither still links to its repository group -- correct place,
    wrong page -- and the report says so on the link.
    """
    path = HERE / "testmo_case_links.json"
    return json.loads(path.read_text()) if path.exists() else {}


def _source_sha():
    """Short SHA of the automation-repo commit this report describes.

    Taken from automated_tests.json, which extract_tests.py stamps with the ref
    it actually read. It used to shell out to git at ../automation_web_2.0 -- a
    path that only exists locally, so CI produced an empty sha and the report
    header lost its provenance line.
    """
    try:
        inv = json.loads((HERE / "automated_tests.json").read_text())
        return (inv.get("_meta") or {}).get("sha", "")
    except Exception:
        return ""


def merge_regression(web, regression):
    """Fold the regression repository export into the mWEB case list.

    The two exports are complementary. Run 2154 is a run OF repository 3 /
    group 73697 and carries the case names; the repository export has no name
    column but holds the full group, including cases no run covered. So:

      * a case in both  -> keep the run's name, take the repository's richer
                           preconditions/steps, tag it `regression`
      * repository only -> add it, labelled from its TestMO Summary
      * run only        -> the 11 Admin "Product types" cases, tag `other_group`

    Any disagreement on the Automated flag is a hard error: the flag decides
    scope, so the two exports drifting apart would silently move every number.
    """
    by_id = {c["case_id"]: c for c in regression}
    mismatched = {}
    for c in web:
        reg = by_id.pop(c["case_id"], None)
        if reg is None:
            c["source"] = "other_group"
            continue
        c["source"] = "regression"
        if c["automated_flag"] != reg["automated_flag"]:
            mismatched[c["case_id"]] = (c["automated_flag"], reg["automated_flag"])
        for field in ("preconditions", "steps"):
            if reg.get(field) and not c.get(field):
                c[field] = reg[field]
    if mismatched:
        raise SystemExit(
            "Automated flag differs between the run export and the regression "
            f"repository export: {mismatched}")

    # Whatever is left existed only in the repository -- no run has covered it.
    for c in by_id.values():
        c["source"] = "regression"
        c["folder"] = c.get("folder") or "Regression repository (not in run 2154)"
    return web + list(by_id.values())


def load(name, required=True):
    path = HERE / name
    if not path.exists():
        if not required:
            return None
        raise SystemExit(f"{name} missing -- run `make generate` (or the parse/extract steps) first")
    return json.loads(path.read_text())


# --- Mappings staged against a PR that has not merged yet --------------------
#
# A ref that is not on main is normally a hard build failure: a mapping has to be
# provable against the shipped suite, always. But a reviewed PR whose tests are
# already written should not need a human to come back and re-run anything on
# merge day. An entry here is inert until EVERY one of its refs is on main, then
# applies itself -- so the first CI build after the merge flips the case with the
# evidence note already written. Keyed by (scope, case_id).
PENDING = {
    # (empty -- FALCONS-364 landed in #310 and now lives in the dicts above)
}


def resolve_pending(mapping, inventory, scope):
    """Fold in any staged mapping whose tests have now reached main."""
    for (entry_scope, case_id), value in PENDING.items():
        if entry_scope != scope:
            continue
        refs = value[1]
        missing = [r for r in refs if r not in inventory]
        if not missing:
            mapping[case_id] = value
            print(f"  pending -> landed: case {case_id} ({len(refs)} tests now on main)")
        else:
            print(f"  pending: case {case_id} still waiting on {len(missing)}/{len(refs)} tests")
    return mapping


def apply_mapping(cases, mapping, inventory, label, previous, source=None):
    """Attach refs / status / notes to each case; validate as we go."""
    by_id = {c["case_id"]: c for c in cases}
    unknown = sorted(set(mapping) - set(by_id))
    if unknown:
        raise SystemExit(f"{label}: mapping refers to case ids not in the export: {unknown}")

    prev_ids = {c["case_id"]: c for c in previous}
    links = _case_links()
    for case in cases:
        if source:
            case["source"] = source
        link = links.get(case["case_id"], {})
        if link.get("page"):
            case["page"] = link["page"]
        # The run export is the authority on test_id; a repository export has none.
        if link.get("test_id"):
            case["test_id"] = link["test_id"]
            case["run_id"] = link["run"]
        status, refs, notes = mapping.get(case["case_id"], ("none", [], ""))
        bad = [r for r in refs if r not in inventory]
        if bad:
            raise SystemExit(f"{label} case {case['case_id']}: unknown test refs {bad}")
        if (status == "none") != (not refs):
            raise SystemExit(f"{label} case {case['case_id']}: status '{status}' does not match {len(refs)} refs")
        if status != "none" and not notes.strip():
            raise SystemExit(f"{label} case {case['case_id']}: '{status}' needs a note explaining the evidence")

        case["automated_tests"] = refs
        case["coverage_status"] = status
        case["notes"] = notes
        # A case counts as automated only if something actually runs for it on
        # the targets we ship to. Two ways that fails, both excluded:
        #
        #   hard-skipped  -- @pytest.mark.skip. Nothing runs anywhere.
        #   gated         -- every mapped test is skipif'd on OS or COUNTRY, so
        #                    the case is unproven on the platforms it is skipped
        #                    for. Counting it as automated overstated it.
        #
        # They are kept apart because the work to close them differs: an unskip
        # versus making the test work on the excluded platform.
        skips = [(inventory[r]["skip"] or {}) for r in refs]
        case["skipped_only"] = bool(refs) and all(k.get("type") == "hard" for k in skips)
        case["gated_only"] = bool(refs) and not case["skipped_only"] and all(
            k.get("type") in ("hard", "conditional") for k in skips)
        if case["skipped_only"]:
            case["coverage_status"] = "none"
            case["notes"] = (case["notes"] + " NOT COUNTED AS AUTOMATED: every mapped script is "
                             "hard-skipped, so nothing runs. Closing this is an unskip, not new "
                             "test work.").strip()
        elif case["gated_only"]:
            # Counted as automated, deliberately. Every one of these gates is a
            # product or tooling limitation, not missing test work: Safari cannot
            # type into the Checkout.com iframes; the SA gift-registry screen
            # renders blank (app bug); the iOS cart does not load after a
            # sign-out precondition (FALCONS-288). The tests are written and run
            # green wherever the product allows, so excluding them would drop the
            # coverage figure because the app has a bug -- which is backwards.
            # The limitation is surfaced on the row instead, which says which
            # platform is uncovered and why; a lower percentage cannot.
            gates = sorted({k.get("reason", "")[:110] for k in skips if k.get("type") == "conditional"})
            case["gate_reasons"] = gates
            case["notes"] = (case["notes"] + " LIMITED TO SOME TARGETS: " + "; ".join(gates)).strip()
        locales = set()
        for r in refs:
            locales.update(inventory[r]["locales"])
        case["locales"] = sorted(locales, reverse=True) or ["en"]
        # The repository export carries no Test ID; keep the one we already had.
        if not case["test_id"] and case["case_id"] in prev_ids:
            case["test_id"] = prev_ids[case["case_id"]].get("test_id", "")
    return cases


def reconcile(cases):
    """Where the TestMO Automated flag disagrees with what the code actually does."""
    out = {"no_but_automated": [], "yes_but_none": [], "yes_but_partial": [], "not_planned_but_automated": []}
    for c in cases:
        flag, status = c["automated_flag"].upper(), c["coverage_status"]
        entry = {"case_id": c["case_id"], "name": c["name"], "status": status}
        if flag == "NO" and status == "full":
            out["no_but_automated"].append(entry)
        elif flag == "YES" and status == "none":
            out["yes_but_none"].append(entry)
        elif flag == "YES" and status == "partial":
            out["yes_but_partial"].append(entry)
        elif flag == "NOT PLANNED" and status != "none":
            out["not_planned_but_automated"].append(entry)
    return out


def projection(web, app, plan_gaps, reconciliation):
    """What coverage becomes once TestMO is corrected -- a projection, not a measurement.

    Three corrections, each evidenced elsewhere in this file:
      A. cases flagged YES that nothing covers leave scope ("Not planned")
      B. a case is written for each passing test that has none, and it is covered
      C. cases flagged Not planned that are already automated re-enter scope

    None of these can be applied to the real figures here: A and C are TestMO flag
    decisions, and B would mean inventing case ids. So they are reported
    separately and clearly labelled.
    """
    w, a = tally(web), tally(app)
    yes_but_none = len(reconciliation["web"]["yes_but_none"]) + len(reconciliation["app"]["yes_but_none"])
    web_gaps = sum(1 for g in plan_gaps if g["platform"].startswith("web"))
    app_gaps = sum(1 for g in plan_gaps if g["platform"] == "app")
    np_automated = {k: reconciliation[k]["not_planned_but_automated"] for k in ("web", "app")}

    def apply(t, gaps, drop_yes_none, readmit):
        scope = t["in_scope"] - drop_yes_none + gaps + len(readmit)
        covered = t["covered"] + gaps + sum(1 for e in readmit if e["status"] != "none")
        return {"in_scope": scope, "covered": covered,
                "pct": round(covered / scope * 100) if scope else 0}

    pw = apply(w, web_gaps, len(reconciliation["web"]["yes_but_none"]), np_automated["web"])
    pa = apply(a, app_gaps, len(reconciliation["app"]["yes_but_none"]), np_automated["app"])
    combined = {"in_scope": pw["in_scope"] + pa["in_scope"], "covered": pw["covered"] + pa["covered"]}
    combined["pct"] = round(combined["covered"] / combined["in_scope"] * 100)
    return {
        "web": pw, "app": pa, "combined": combined,
        "actions": [
            {"id": "A", "what": f"Re-flag {yes_but_none} case(s) flagged YES that nothing covers",
             "detail": "Exit Checkout Prompt (C-2337045) — no exit-prompt locator or page method exists on main",
             "effect": "leaves scope; mWEB Checkout folder reaches 8/8"},
            {"id": "B", "what": f"Add {web_gaps + app_gaps} TestMO case(s) for tests that pass but have none",
             "detail": "the cart scenarios FALCONS-336 ported from the app suite; each names the app case to mirror",
             "effect": "enters scope already covered"},
            {"id": "C", "what": f"Re-flag {len(np_automated['web']) + len(np_automated['app'])} case(s) marked Not planned that have automation mapped",
             # Derived, not hardcoded: the old text still named a brand-page case
             # that had since been reclassified as not automated.
             "detail": ", ".join(f"C-{e['case_id']}" for k in ("web", "app") for e in np_automated[k]) or "none",
             "effect": "enters scope, already covered"},
        ],
    }


def statuses(data):
    """Every case's status and scope, keyed "web:<id>" / "app:<id>"."""
    out = {}
    for platform, key in (("web", "testmo_tests"), ("app", "app_testmo_tests")):
        for c in data.get(key) or []:
            out[f"{platform}:{c['case_id']}"] = (c["coverage_status"], c.get("in_scope", True), c["name"])
    return out


def history_point(data, previous, day):
    """One point on the coverage trend, or None if no in-scope case moved.

    `previous` is statuses() of the build before. Recording only when a case
    changes keeps the trend to the moments the number actually moved, and makes
    re-running the build idempotent.
    """
    now = statuses(data)
    changes = []
    for key, (status, in_scope, name) in now.items():
        old = previous.get(key)
        was = old[0] if old and old[1] else ("new" if not old else "out")
        if in_scope and was != status:
            changes.append({"case": key, "name": name[:90], "from": was, "to": status})
        elif not in_scope and old and old[1]:
            changes.append({"case": key, "name": name[:90], "from": old[0], "to": "out"})
    if previous and not changes:
        return None

    def share(platform):
        scoped = [v for k, v in now.items() if k.startswith(platform + ":") and v[1]]
        return [sum(1 for v in scoped if v[0] != "none"), sum(1 for v in scoped if v[0] == "full"), len(scoped)]

    tests = data.get("automated_tests") or {}
    return {"date": day, "sha": (data.get("metadata") or {}).get("source_sha", ""),
            "web": share("web"), "app": share("app"),   # [covered, full, in scope]
            "tests": sum(len(v) for k, v in tests.items() if k != "_meta"),
            "changes": [] if not previous else changes}


def tally(cases):
    scoped = [c for c in cases if c["in_scope"]]
    full = sum(1 for c in scoped if c["coverage_status"] == "full")
    partial = sum(1 for c in scoped if c["coverage_status"] == "partial")
    return {"total": len(cases), "in_scope": len(scoped), "out_of_scope": len(cases) - len(scoped),
            "full": full, "partial": partial, "covered": full + partial,
            "none": len(scoped) - full - partial,
            "pct": round((full + partial) / len(scoped) * 100) if scoped else 0,
            "pct_full": round(full / len(scoped) * 100) if scoped else 0}


def main():
    web = load("testmo_tests.json")
    regression = load("web_regression_tests.json", required=False)
    for c in web:
        c.setdefault("name_source", "testmo")
    app = load("app_testmo_tests.json")
    automated = load("automated_tests.json")
    inventory = {t["ref"]: t for k, v in automated.items() if k != "_meta" for t in v}

    prev_path = HERE / "mapping.json"
    prev = json.loads(prev_path.read_text()) if prev_path.exists() else {}

    # Merge the repository export in BEFORE mapping, so cases that exist only
    # there go through the same validation as everything else.
    reg_stats = None
    if regression:
        web = merge_regression(web, regression)
        reg_stats = {
            "total_cases": sum(1 for c in web if c["source"] == "regression"),
            "in_scope": sum(1 for c in web if c["source"] == "regression" and c["in_scope"]),
            "named_from_summary": sum(1 for c in web if c["source"] == "regression"
                                      and c.get("name_source") == "summary"),
            "other_group": sum(1 for c in web if c["source"] == "other_group"),
        }
    else:
        for c in web:
            c.setdefault("source", "regression")

    web = apply_mapping(web, resolve_pending(WEB_MAPPING, inventory, "web"),
                        inventory, "mWEB", prev.get("testmo_tests", []))
    app = apply_mapping(app, resolve_pending(APP_MAPPING, inventory, "app"),
                        inventory, "App", prev.get("app_testmo_tests", []),
                        source="release_check")

    mapped = {r for c in web + app for r in c["automated_tests"]}
    flat = list(inventory.values())
    hard = [t for t in flat if (t["skip"] or {}).get("type") == "hard"]
    cond = [t for t in flat if (t["skip"] or {}).get("type") == "conditional"]

    web_t, app_t = tally(web), tally(app)
    by_source = {src: tally([c for c in web if c.get("source") == src])
                 for src in sorted({c.get("source") for c in web if c.get("source")})}
    combined = {
        "in_scope": web_t["in_scope"] + app_t["in_scope"],
        "full": web_t["full"] + app_t["full"],
        "partial": web_t["partial"] + app_t["partial"],
    }
    combined["covered"] = combined["full"] + combined["partial"]
    combined["pct"] = round(combined["covered"] / combined["in_scope"] * 100)
    combined["pct_full"] = round(combined["full"] / combined["in_scope"] * 100)

    plan_gaps = [
        {"ref": ref, "platform": inventory[ref]["platform"],
         "path": inventory[ref]["path"],
         "mirrors_case": PLAN_GAPS[ref][0], "mirrors_name": PLAN_GAPS[ref][1]}
        for ref in sorted(PLAN_GAPS) if ref in inventory and ref not in mapped
    ]
    reconciliation = {"web": reconcile(web), "app": reconcile(app)}

    out = {
        "testmo_tests": web,
        "app_testmo_tests": app,
        "automated_tests": {k: v for k, v in automated.items() if k != "_meta"},
        "arabic": ARABIC,
        "flag_reconciliation": reconciliation,
        "unmapped_tests": sorted(r for r in inventory if r not in mapped),
        "plan_gaps": plan_gaps,
        "metadata": {
            # Bumped whenever the shape changes. index.html refuses a cached
            # gist payload with an older schema so it never renders bare names
            # against ref-based code.
            "schema": 2,
            "last_updated": date.today().isoformat(),
            "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
            "source_sha": _source_sha(),
            "source_branch": "origin/main",
            "scope_rule": "Automated in [YES, NO]; 'Not planned' cases are kept but excluded from every percentage",
            "testmo_url_web": "https://mumzworld.testmo.net/runs/view/2154",
            "testmo_url_app": "https://mumzworld.testmo.net/repositories/9?group_id=110524",
            "testmo_url_web_regression": "https://mumzworld.testmo.net/repositories/3?group_id=73697",
            "testmo_data_as_of": _source_dates(),
            "sources": {
                "mweb": "TestMO repository 3 / group 73697 (regression repository), read via run 2154 -- "
                        "the run export is what carries the case names; the repository export has no Case column",
                "mweb_other_group": "11 Admin 'Product types' cases sit outside group 73697; all are Not planned",
                "app": "TestMO repository 9 / group 110524 (release checklist); exported as testmo-export-repository-241",
            },
            "coverage": {"web": web_t, "app": app_t, "combined": combined,
                         "web_by_source": by_source},
            "projection": projection(web, app, plan_gaps, reconciliation),
            "regression_repo": reg_stats,
            "platforms": {k: len(v) for k, v in automated.items() if k != "_meta"},
            "total_automated_tests": len(flat),
            "active_tests": len(flat) - len(hard) - len(cond),
            "skipped_hard": len(hard),
            "cases_not_running": {
                "hard_skipped": sum(1 for c in web + app if c["in_scope"] and c.get("skipped_only")),
                "gated": sum(1 for c in web + app if c["in_scope"] and c.get("gated_only")),
            },
            "gate_note": "Hard-skipped cases are not counted as automated: nothing runs. "
                         "Platform-gated cases are counted -- they run wherever the product allows, "
                         "and every gate is a product or tooling limitation rather than missing test "
                         "work -- with the limitation shown on the case.",
            "skipped_conditional": len(cond),
            "links": {
                "direct": sum(1 for c in web + app if c.get("run_id")),
                "listing_with_page": sum(1 for c in web + app if not c.get("run_id") and c.get("page")),
                "listing_no_page": sum(1 for c in web + app if not c.get("run_id") and not c.get("page")),
            },
            "unmapped_count": len(inventory) - len(mapped),
            "plan_gap_count": sum(1 for r in PLAN_GAPS if r in inventory and r not in mapped),
            "unmapped_and_skipped": sum(
                1 for r in inventory
                if r not in mapped and (inventory[r]["skip"] or {}).get("type") == "hard"),
            "arabic_ready_tests": sum(1 for t in flat if "ar" in t["locales"]),
            # The headline percentage can sit still while real work lands: a new test
            # that deepens a case TestMO already counts changes no case's status. The
            # suite size is the honest companion number, so record where it started.
            "baseline": {"tests": 131, "date": "2026-09-02", "sha": "8a95571",
                         "what": "the re-map against main"},
        },
    }
    # Carried forward from the previous build, so CI extends the trend on its own.
    history = list((prev.get("metadata") or {}).get("history") or [])
    point = history_point(out, statuses(prev) if prev else {}, date.today().isoformat())
    if point:
        history.append(point)
    out["metadata"]["history"] = history
    (HERE / "mapping.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))

    print(f"mWEB  {web_t['full']} full + {web_t['partial']} partial = {web_t['covered']}/{web_t['in_scope']} "
          f"({web_t['pct']}%)   [{web_t['out_of_scope']} out of scope]")
    if reg_stats:
        print(f"      regression repo 3/73697 mirrored: {reg_stats['total_cases']} cases, "
              f"{reg_stats['in_scope']} in scope, flags agree "
              f"({reg_stats['named_from_summary']} labelled from Summary; "
              f"{reg_stats['other_group']} Admin cases outside the group)")
    for src, t in by_source.items():
        print(f"  - {src:15s} {t['full']} full + {t['partial']} partial = "
              f"{t['covered']}/{t['in_scope']} ({t['pct']}%)   [{t['out_of_scope']} out of scope]")
    print(f"App   {app_t['full']} full + {app_t['partial']} partial = {app_t['covered']}/{app_t['in_scope']} "
          f"({app_t['pct']}%)   [{app_t['out_of_scope']} out of scope]")
    print(f"Total {combined['full']} full + {combined['partial']} partial = "
          f"{combined['covered']}/{combined['in_scope']} ({combined['pct']}%)")
    print(f"Tests {len(flat)} ({len(hard)} hard-skipped, {len(cond)} OS-gated), "
          f"{len(inventory) - len(mapped)} unmapped -> mapping.json")


if __name__ == "__main__":
    main()

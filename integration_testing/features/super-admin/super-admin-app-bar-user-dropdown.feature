Feature: Super admin sees that their User type is *Super admin* in the user dropdown

  Background:
    Given I am signed in to Kolibri as a super admin

  Scenario: Super admin can see they are a super admin
    When I click on the user dropdown on the right side of the action bar
    Then I can see that my user type is super admin

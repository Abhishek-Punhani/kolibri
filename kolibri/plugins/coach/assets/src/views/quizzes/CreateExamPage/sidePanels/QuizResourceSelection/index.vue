<template>

  <SidePanelModal
    alignment="right"
    sidePanelWidth="700px"
    closeButtonIconType="close"
    @closePanel="handleClosePanel"
    @shouldFocusFirstEl="() => null"
  >
    <template #header>
      <div style="display: flex; gap: 8px; align-items: center">
        <KIconButton
          v-if="goBack"
          icon="back"
          @click="goBack()"
        />
        <h1 class="side-panel-title">{{ title }}</h1>
      </div>
    </template>
    <template #default="{ isScrolled }">
      <div v-if="loading">
        <KCircularLoader />
      </div>

      <div
        v-if="maximumContentSelectedWarning"
        class="alert-warning"
        :class="{
          shadow: isScrolled,
        }"
        :style="{
          background: $themePalette.lightblue.v_100,
        }"
      >
        <span>
          {{ maximumContentSelectedWarning }}
        </span>
      </div>
      <router-view
        v-if="!loading"
        :setTitle="value => (title = value)"
        :setGoBack="value => (goBack = value)"
        :setContinueAction="value => (continueAction = value)"
        :sectionTitle="sectionTitle"
        :selectedResources="workingResourcePool"
        :topic="topic"
        :treeFetch="treeFetch"
        :channelsFetch="channelsFetch"
        :bookmarksFetch="bookmarksFetch"
        :selectAllRules="selectAllRules"
        :selectionRules="selectionRules"
        :settings.sync="settings"
        :target="SelectionTarget.QUIZ"
        :contentCardMessage="contentCardMessage"
        :getResourceLink="getResourceLink"
        @selectResources="addToWorkingResourcePool"
        @deselectResources="removeFromWorkingResourcePool"
        @setSelectedResources="setWorkingResourcePool"
      />
      <KModal
        v-if="showCloseConfirmation"
        :submitText="coreString('continueAction')"
        :cancelText="coreString('cancelAction')"
        :title="closeConfirmationTitle$()"
        @cancel="handleCancelClose"
        @submit="handleClosePanel"
      >
        {{ closeConfirmationMessage$() }}
      </KModal>
    </template>

    <template #bottomNavigation>
      <div class="bottom-nav-container">
        <KButton
          v-if="continueAction"
          :disabled="continueAction.disabled"
          :text="coreString('continueAction')"
          @click="continueAction.handler"
        />
        <template v-else>
          <div v-if="!settings.selectPracticeQuiz">
            <span v-if="tooManyQuestions">
              {{
                tooManyQuestions$({
                  count: settings.questionCount,
                })
              }}
            </span>
            <KRouterLink
              v-else-if="
                workingResourcePool.length > 0 &&
                  $route.name !== PageNames.QUIZ_PREVIEW_SELECTED_RESOURCES
              "
              :to="{ name: PageNames.QUIZ_PREVIEW_SELECTED_RESOURCES }"
            >
              {{
                numberOfSelectedResources$({
                  count: workingResourcePool.length,
                })
              }}
            </KRouterLink>
          </div>
          <div class="save-button-wrapper">
            <KButton
              primary
              :text="
                settings.selectPracticeQuiz
                  ? selectQuiz$()
                  : addNumberOfQuestions$({ count: Math.max(1, settings.questionCount) })
              "
              :disabled="disableSave"
              @click="saveSelectedResource"
            />
          </div>
        </template>
      </div>
    </template>
  </SidePanelModal>

</template>


<script>

  import get from 'lodash/get';
  import uniqWith from 'lodash/uniqWith';
  import isEqual from 'lodash/isEqual';
  import { useMemoize } from '@vueuse/core';
  import {
    displaySectionTitle,
    enhancedQuizManagementStrings,
  } from 'kolibri-common/strings/enhancedQuizManagementStrings';
  import { searchAndFilterStrings } from 'kolibri-common/strings/searchAndFilterStrings';
  import { computed, ref, getCurrentInstance, watch } from 'vue';
  import commonCoreStrings from 'kolibri/uiText/commonCoreStrings';
  import { ContentNodeKinds, MAX_QUESTIONS_PER_QUIZ_SECTION } from 'kolibri/constants';
  import SidePanelModal from 'kolibri-common/components/SidePanelModal';
  import { coachStrings } from '../../../../common/commonCoachStrings';
  import { exerciseToQuestionArray } from '../../../../../utils/selectQuestions';
  import { PageNames } from '../../../../../constants/index';
  import useQuizResources from '../../../../../composables/useQuizResources';
  import { injectQuizCreation } from '../../../../../composables/useQuizCreation';
  import useResourceSelection from '../../../../../composables/useResourceSelection';
  import { SelectionTarget } from '../../../../common/resourceSelection/contants';

  export default {
    name: 'ResourceSelection',
    components: {
      SidePanelModal,
    },
    mixins: [commonCoreStrings],
    setup() {
      const { $store, $router } = getCurrentInstance().proxy;
      const route = computed(() => $store.state.route);
      const {
        activeSection,
        activeSectionIndex,
        updateSection,
        addQuestionsToSectionFromResources,
        allQuestionsInQuiz,
        activeQuestions,
        addSection,
      } = injectQuizCreation();
      const showCloseConfirmation = ref(false);

      const { selectPracticeQuiz } = route.value.query;

      const settings = ref({
        maxQuestions: null,
        questionCount: null,
        isChoosingManually: null,
        selectPracticeQuiz,
      });
      watch(
        activeQuestions,
        () => {
          const newSettings = { ...settings.value };
          newSettings.maxQuestions = MAX_QUESTIONS_PER_QUIZ_SECTION - activeQuestions.value.length;
          if (newSettings.questionCount === null) {
            // initialize questionCount if it hasn't been set yet
            newSettings.questionCount = Math.min(10, newSettings.maxQuestions);
          }
          settings.value = newSettings;
        },
        { immediate: true },
      );

      const {
        questionsUnusedInSection$,
        tooManyQuestions$,
        selectQuiz$,
        addNumberOfQuestions$,
        maximumResourcesSelectedWarning$,
        maximumQuestionsSelectedWarning$,
      } = enhancedQuizManagementStrings;

      const { closeConfirmationTitle$, closeConfirmationMessage$ } = coachStrings;

      /**
       * @type {Ref<QuizExercise[]>} - The uncommitted version of the section's resource_pool
       */
      const workingResourcePool = ref([]);

      /**
       * @param {QuizExercise[]} resources
       * @affects workingResourcePool -- Updates it with the given resources and is ensured to have
       * a list of unique resources to avoid unnecessary duplication
       */
      function addToWorkingResourcePool(resources = []) {
        workingResourcePool.value = uniqWith(
          [
            ...workingResourcePool.value,
            ...resources.filter(r => r.kind === ContentNodeKinds.EXERCISE),
          ],
          isEqual,
        );
      }

      /**
       * @param {QuizExercise} content
       * @affects workingResourcePool - Remove given quiz exercise from workingResourcePool
       */
      function removeFromWorkingResourcePool(resources = []) {
        workingResourcePool.value = workingResourcePool.value.filter(
          obj => !resources.some(r => r.id === obj.id),
        );
      }

      /**
       * @affects workingResourcePool - Resets the workingResourcePool to the previous state
       */
      function setWorkingResourcePool(resources = []) {
        workingResourcePool.value = resources;
      }

      const { annotateTopicsWithDescendantCounts } = useQuizResources();

      const unusedQuestionsCount = useMemoize(content => {
        const questionItems = content.assessmentmetadata.assessment_item_ids.map(
          aid => `${content.id}:${aid}`,
        );
        const questionsItemsAlreadyUsed = allQuestionsInQuiz.value
          .map(q => q.item)
          .filter(i => questionItems.includes(i));
        const questionItemsAvailable = questionItems.length - questionsItemsAlreadyUsed.length;
        return questionItemsAvailable;
      });

      const isPracticeQuiz = item =>
        !selectPracticeQuiz || get(item, ['options', 'modality'], false) === 'QUIZ';

      const { topic, loading, treeFetch, channelsFetch, bookmarksFetch } = useResourceSelection({
        bookmarks: {
          filters: { kind: ContentNodeKinds.EXERCISE },
          annotator: results => results.filter(isPracticeQuiz),
        },
        channels: {
          filters: {
            contains_exercise: true,
            contains_quiz: selectPracticeQuiz ? true : null,
          },
          annotator: results =>
            annotateTopicsWithDescendantCounts(
              results.map(channel => {
                return {
                  ...channel,
                  id: channel.root,
                  title: channel.name,
                  kind: ContentNodeKinds.CHANNEL,
                  is_leaf: false,
                };
              }),
            ),
        },
        topicTree: {
          filters: {
            kind_in: [ContentNodeKinds.EXERCISE, ContentNodeKinds.TOPIC],
            contains_quiz: selectPracticeQuiz ? true : null,
          },
          annotator: annotateTopicsWithDescendantCounts,
        },
      });

      function handleCancelClose() {
        showCloseConfirmation.value = false;
      }

      function handleClosePanel() {
        $router.push({
          name: PageNames.EXAM_CREATION_ROOT,
          params: {
            classId: route.value.params.classId,
            quizId: route.value.params.quizId,
            sectionIndex: route.value.params.sectionIndex,
          },
          query: { ...route.value.query },
        });
      }

      const workingPoolHasChanged = computed(() => {
        return Boolean(workingResourcePool.value.length);
      });

      const workingPoolUnusedQuestions = computed(() => {
        return workingResourcePool.value.reduce((acc, content) => {
          return acc + unusedQuestionsCount(content);
        }, 0);
      });

      const tooManyQuestions = computed(() => {
        return workingResourcePool.value.length > settings.value.questionCount;
      });

      const disableSave = computed(() => {
        if (selectPracticeQuiz) {
          return !workingPoolHasChanged.value;
        }
        return (
          !workingPoolHasChanged.value ||
          workingPoolUnusedQuestions.value < settings.value.questionCount ||
          settings.value.questionCount < 1 ||
          tooManyQuestions.value ||
          settings.value.questionCount.value > settings.value.maxQuestions
        );
      });

      const title = ref('');
      const goBack = ref(null);
      const continueAction = ref(null);
      const sectionTitle = computed(() =>
        displaySectionTitle(activeSection.value, activeSectionIndex.value),
      );

      const remainingSelectableContent = computed(
        () => settings.value.questionCount - workingResourcePool.value.length,
      );

      const selectAllRules = computed(() => [
        contentList => contentList.length <= remainingSelectableContent.value,
      ]);

      const selectionRules = computed(() => [() => remainingSelectableContent.value > 0]);

      const maximumContentSelectedWarning = computed(() => {
        if (settings.value.questionCount <= 0 || remainingSelectableContent.value > 0) {
          return null;
        }
        if (settings.value.isChoosingManually) {
          return maximumQuestionsSelectedWarning$();
        }
        return maximumResourcesSelectedWarning$();
      });

      const { numberOfSelectedResources$ } = searchAndFilterStrings;

      return {
        title,
        goBack,
        PageNames,
        continueAction,
        SelectionTarget,
        sectionTitle,
        unusedQuestionsCount,
        activeSectionIndex,
        addSection,
        workingPoolHasChanged,
        tooManyQuestions,
        handleClosePanel,
        handleCancelClose,
        topic,
        showCloseConfirmation,
        treeFetch,
        channelsFetch,
        bookmarksFetch,
        loading,
        selectionRules,
        selectAllRules,
        maximumContentSelectedWarning,
        addToWorkingResourcePool,
        removeFromWorkingResourcePool,
        setWorkingResourcePool,
        settings,
        disableSave,
        closeConfirmationMessage$,
        closeConfirmationTitle$,
        tooManyQuestions$,
        questionsUnusedInSection$,
        updateSection,
        addQuestionsToSectionFromResources,
        workingResourcePool,
        selectQuiz$,
        addNumberOfQuestions$,
        numberOfSelectedResources$,
      };
    },
    beforeRouteLeave(_, __, next) {
      if (!this.showCloseConfirmation && this.workingPoolHasChanged) {
        this.showCloseConfirmation = true;
        next(false);
      } else {
        next();
      }
    },
    methods: {
      saveSelectedResource() {
        if (this.settings.selectPracticeQuiz) {
          if (this.workingResourcePool.length !== 1) {
            throw new Error('Only one resource can be selected for a practice quiz');
          }
          const remainder = exerciseToQuestionArray(this.workingResourcePool[0]);

          let sectionIndex = this.activeSectionIndex;
          while (remainder.length) {
            if (sectionIndex !== this.activeSectionIndex) {
              this.addSection();
            }
            const questions = remainder.splice(0, MAX_QUESTIONS_PER_QUIZ_SECTION);
            this.updateSection({
              sectionIndex,
              questions,
              resourcePool: this.workingResourcePool,
            });
            sectionIndex++;
          }
        } else {
          this.addQuestionsToSectionFromResources({
            sectionIndex: this.activeSectionIndex,
            resourcePool: this.workingResourcePool,
            questionCount: this.settings.questionCount,
          });
        }

        this.setWorkingResourcePool();
        this.$router.replace({
          name: PageNames.EXAM_CREATION_ROOT,
          params: {
            ...this.$route.params,
          },
        });
      },
      // The message put onto the content's card when listed
      contentCardMessage(content) {
        if (this.settings.selectPracticeQuiz) {
          return;
        }
        if (content.kind !== ContentNodeKinds.EXERCISE) {
          return;
        }

        const count = this.unusedQuestionsCount(content);

        if (count === -1) {
          // If for some reason we're getting a content type that we don't know how to handle
          // we'll just return nothing to avoid displaying a nonsensical message
          return;
        }

        return this.questionsUnusedInSection$({
          count,
        });
      },
      getResourceLink(resourceId) {
        return {
          name: PageNames.QUIZ_PREVIEW_RESOURCE,
          query: {
            ...this.$route.query,
            contentId: resourceId,
          },
        };
      },
    },
  };

</script>


<style lang="scss" scoped>

  @import '~kolibri-design-system/lib/styles/definitions';

  .side-panel-title {
    margin-top: 20px;
    font-size: 18px;
  }

  .bottom-nav-container {
    display: flex;
    gap: 16px;
    justify-content: flex-end;
    width: 100%;

    .save-button-wrapper {
      display: flex;
      align-items: center;
      min-height: 40px;
    }
  }

  .alert-warning {
    position: sticky;
    top: 0;
    z-index: 1;
    width: 100%;
    padding: 16px;
    margin-bottom: 16px;
    border-radius: 4px;
    transition: $core-time ease;

    &.shadow {
      @extend %dropshadow-2dp;
    }
  }

</style>

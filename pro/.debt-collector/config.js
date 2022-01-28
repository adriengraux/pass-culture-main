module.exports = {
  collectFrom: './src/**/*',
  fileRules: [
    {
      title: 'remove react-final-form dependency',
      id: 'REMOVE_FINAL_FORM',
      description:
        'we should use formik in combination with the ui-kit forms components instead',
      debtScore: 3,
      tags: ['dependency', 'forms', 'deprecated', 'react-final-form'],
      matchGlob: '**/*.{ts,tsx,js,jsx}',
      matchRule: ({ isImportingFrom }) => isImportingFrom('react-final-form'),
    },
    {
      title: 'remove custom inputs and forms',
      id: 'REMOVE_CUSTOM_FORM',
      description:
        'we should use formik in combination with the ui-kit forms components instead',
      debtScore: 3,
      tags: ['dependency', 'forms', 'deprecated', 'custom forms'],
      matchGlob: '**/*.{ts,tsx,js,jsx}',
      matchRule: ({ isImportingFrom }) =>
        isImportingFrom('components/layout/inputs'),
    },
    {
      title: 'remove forms components from layout/form',
      id: 'REMOVE_FINAL_FORM_COMPONENTS',
      description:
        'we should use formik in combination with the ui-kit forms components instead',
      debtScore: 1,
      tags: ['dependency', 'forms', 'deprecated'],
      matchGlob: '**/*.{ts,tsx,js,jsx}',
      matchRule: ({ isImportingFrom }) =>
        isImportingFrom('components/layout/form'),
    },
    {
      title:
        'should follow ui-kit / new_components / screen / route directory structure',
      id: 'DIRECTORY_STRUCTURE',
      description: 'see documentation here',
      debtScore: 1,
      tags: ['directory structure'],
      matchGlob: './src/components/**/*.{ts,tsx,js,jsx}',
    },
    {
      title: 'should migrate js and jsx files to typescript',
      id: 'TYPESCRIPT_MIGRATION',
      description: 'see documentation here',
      debtScore: 3,
      tags: ['typescript'],
      matchGlob: '**/*.{js,jsx}',
    },
    {
      title:
        "use css-modules `style['classe']` or use ui-kit instead of global classes",
      id: 'SCSS_MODULE',
      description:
        'imports local scss file and store it into a "style" constant, then use className={style[\'ma-classe\']}',
      debtScore: 1,
      tags: ['scss module', 'styles'],
      matchGlob: '**/*.{ts,tsx,js,jsx}',
      matchRule: ({ find }) =>
        find(`className="`) +
        find(`className={classnames('`) +
        find(`className={cx('`) +
        find(`className={cn('`),
    },
    {
      title: 'should not use redux-saga anymore',
      id: 'DEPRECATED_REDUX_SAGA',
      description: '',
      debtScore: 5,
      tags: ['deprecated', 'redux'],
      matchGlob: '**/*.{ts,tsx,js,jsx}',
      matchRule: ({ isImportingFrom }) => isImportingFrom('redux-saga'),
    },
    {
      title: 'should migrate from enzyme to RTL',
      id: 'DEPRECATED_ENZYME_TO_RTL',
      description: '',
      debtScore: 5,
      tags: ['rtl', 'tests'],
      matchGlob: ['**/*.spec.{ts,tsx,js,jsx}', '**/*.specs.{ts,tsx,js,jsx}'],
      matchRule: ({ isImportingFrom }) => isImportingFrom('enzyme'),
    },
    {
      title: 'should use functional components instead of classes',
      id: 'FUNCTIONAL_COMPONENTS',
      description: '',
      debtScore: 3,
      tags: ['deprecated', 'functional'],
      matchGlob: '**/*.{ts,tsx,js,jsx}',
      matchRule: ({ find }) =>
        find('extends Component') +
        find('extends React.Component') +
        find('extends PureComponent') +
        find('extends React.PureComponent'),
    },
    {
      title: 'should not use act() or await render() in tests',
      id: 'CORRECT_ASYNC_TESTING',
      description:
        'use await waitFor, await findBy.., await waitForElementToBeRemoved instead',
      debtScore: 1,
      tags: ['rtl', 'tests'],
      matchGlob: ['**/*.spec.{ts,tsx,js,jsx}', '**/*.specs.{ts,tsx,js,jsx}'],
      matchRule: ({ find }) => find('await act') + find('await render'),
    },
    {
      title: 'should not use withQueryRouter or withRouter',
      id: 'DEPRECATED_WITH_QUERY_ROUTER',
      description:
        'prefer hooks for routers (https://reactrouter.com/web/api/Hooks)',
      debtScore: 2,
      tags: ['deprecated', 'hoc', 'functional'],
      matchGlob: '**/*.{ts,tsx,js,jsx}',
      matchRule: ({ find }) => find('withQueryRouter') + find('withRouter'),
    },
    {
      title: 'should not use connect hoc',
      id: 'DEPRECATED_REDUX_CONNECT_HOC',
      description:
        'prefer useSelector hook vs connect for redux (https://react-redux.js.org/api/hooks)',
      debtScore: 2,
      tags: ['deprecated', 'hoc', 'functional', 'redux'],
      matchGlob: '**/*.{ts,tsx,js,jsx}',
      matchRule: ({ find }) => find('import { connect'),
    },
    {
      title: 'should not be too deep into the directory structure',
      id: 'NESTED_TOO_DEEP',
      description:
        'prefer useSelector hook vs connect for redux (https://react-redux.js.org/api/hooks)',
      debtScore: 2,
      tags: ['deprecated', 'hoc', 'functional', 'redux'],
      matchGlob: '**/*.{ts,tsx,js,jsx,scss,json}',
      matchRule: ({ directoryDepth }) => (directoryDepth > 6 ? 1 : 0),
    },
    {
      title: 'should delete styleguide, and migrate components in storybook',
      id: 'REMOVE_STYLEGUIDE_PAGES',
      debtScore: 1,
      tags: ['deprecated', 'components', 'design system'],
      matchGlob: './src/components/pages/Styleguide/**/*.*',
    },
    {
      title:
        'should migrate everything in hoc directory and create hooks instead',
      id: 'REMOVE_HOC_DIRECTORY',
      debtScore: 2,
      tags: ['deprecated', 'hoc', 'functional'],
      matchGlob: './src/components/hocs/**/*.*',
    },
    {
      title:
        'should migrate all global SCSS files within the components as scss modules',
      id: 'REMOVE_GLOBAL_SCSS',
      debtScore: 2,
      tags: ['scss module', 'styles'],
      matchGlob: [
        './src/styles/components/**/*.scss',
        './src/styles/global/**/*.scss',
      ],
    },
    {
      title:
        'should use the ui-kit Title component instead of h1 h2 etc. directly',
      id: 'USE_TITLE_COMPONENT',
      debtScore: 1,
      tags: ['design system', 'typography'],
      matchGlob: './src/**/*.{tsx,jsx,}',
      matchRule: ({ find }) =>
        find('<h1') +
        find('<h2') +
        find('<h3') +
        find('<h4') +
        find('<h5') +
        find('<h6'),
    },
    {
      title:
        'should use the ui-kit Button component instead of buttons classes',
      id: 'USE_BUTTON_COMPONENT',
      debtScore: 1,
      tags: ['design system', 'buttons'],
      matchGlob: './src/**/*.{tsx,jsx,}',
      matchRule: ({ find }) =>
        find('primary-button') +
        find('primary-link') +
        find('secondary-button') +
        find('secondary-link') +
        find('tertiary-button') +
        find('tertiary-link') +
        find('quaternary-button') +
        find('<button'),
    },
  ],
  eslintConfigPath: `./.debt-collector/.eslintrctoto.js`,
  eslintRules: [
    {
      title:
        'should split this file with too many lines (max allowed : 300 lines)',
      id: 'TOO_MANY_LINES_IN_FILE',
      description: '',
      debtScore: 2,
      tags: ['complexity', 'eslint'],
      matchGlob: '**/*.{ts,tsx,js,jsx}',
      matchESLintRule: ({ containRuleIdMessage }) =>
        containRuleIdMessage('max-lines'),
    },
    {
      title:
        'should split function into smaller parts (max allowed : 50 lines)',
      id: 'TOO_MANY_LINE_IN_FUNCTION',
      description: '',
      debtScore: 1,
      tags: ['complexity', 'eslint'],
      matchGlob: '**/*.{ts,tsx,js,jsx}',
      matchESLintRule: ({ containRuleIdMessage }) =>
        containRuleIdMessage('max-lines-per-function'),
    },
    {
      title: 'should fix eslint react testing library errors',
      id: 'REACT_TESTING_LIBRARY_ESLINT',
      description: '',
      debtScore: 2,
      tags: ['rtl', 'tests', 'eslint'],
      matchGlob: ['**/*.spec.{ts,tsx,js,jsx}', '**/*.specs.{ts,tsx,js,jsx}'],
      matchESLintRule: ({ containMessageFromPlugin }) =>
        containMessageFromPlugin('testing-library/'),
    },
  ],
}

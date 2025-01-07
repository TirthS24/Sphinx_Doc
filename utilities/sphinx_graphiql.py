import fett
from docutils import statemachine
from docutils.utils.error_reporting import ErrorString
from docutils.parsers.rst import Directive


class SphinxGraphiQL(Directive):
    has_content = False
    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {"query": str, "response": str, "endpoint": str, "view_only": str}

    GRAPHIQL_TEMPLATE = '''
    .. raw:: html
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/graphiql/2.0.9/graphiql.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/react/17.0.2/umd/react.production.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/react-dom/17.0.2/umd/react-dom.production.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/graphiql/2.0.9/graphiql.min.js"></script>
    <div id="graphiql" style="height: 80vh; width:120vh;"></div>
    <script>
        const graphQLFetcher = (graphQLParams) => {
        return fetch('{{ endpoint }}', {
            method: 'POST',
            headers: {
            'Content-Type': 'application/json',
            ...JSON.parse('{{ headers }}')
            },
            body: JSON.stringify(graphQLParams),
        }).then(response => response.json());
        };
        ReactDOM.render(
        React.createElement(GraphiQL, { fetcher: graphQLFetcher }),
        document.getElementById('graphiql')
        );
    </script>
    '''

    def run(self):
        raw_template = fett.Template(self.GRAPHIQL_TEMPLATE)
        try:
            rendered_template = raw_template.render(self.options)
        except Exception as error:
            raise self.severe('Failed to render template: {}'.format(ErrorString(error)))

        rendered_lines = statemachine.string2lines(rendered_template, 4, convert_whitespace=1)

        self.state_machine.insert_input(rendered_lines, '')

        return []


"""This command is to update the information of the documents.
Some examples of the usage are given below

Examples
^^^^^^^^

- Update a document automatically and interactively
  (searching by ``doi`` number in *crossref*, or in other sources...)

    .. code::

        papis update --auto -i "author : dyson"

- Update your library from a bib(la)tex file where many entries are listed.
  papis will try to look for documents in your library that match these
  entries and will ask you entry per entry to update it (of course this is
  done if you use the ``-i`` flag for interactively doing it). In the example
  ``libraryfile.bib`` is a file containing many entries.

    .. code::

        papis update --from bibtex libraryfile.bib -i

- Tag all einstein papers with the tag classics

    .. code::

        papis update --all --set tags classics einstein

and add the tag of ``physics`` to all papers tagged as ``classics``

    .. code::

        papis update --all --set tags '{doc[tags]} physics' einstein

Cli
^^^
.. click:: papis.commands.update:cli
    :prog: papis update
"""

import colorama
import logging
import papis.utils
import papis.strings
import papis.downloaders
import papis.document
import papis.database
import papis.pick
import papis.cli
import papis.importer
import click


def _update_with_database(document):
    document.save()
    papis.database.get().update(document)


def run(document, data=dict(), force=False):
    # Keep the ref the same, otherwise issues can be caused when
    # writing LaTeX documents and all the ref's change
    data['ref'] = document['ref']
    document.update(data)
    _update_with_database(document)


@click.command("update")
@click.help_option('--help', '-h')
@papis.cli.query_option()
@papis.cli.doc_folder_option()
@click.option(
    "-i/-b",
    "--interactive/--no-interactive",
    help="Interactive or batch mode",
    default=True
)
@click.option(
    "-f",
    "--force",
    help="Force update, overwrite conflicting information",
    default=False,
    is_flag=True
)
@click.option(
    "--auto",
    help="Try to parse information from different sources",
    default=False,
    is_flag=True
)
@click.option(
    "--all",
    help="Update all entries in library",
    default=False,
    is_flag=True
)
@click.option(
    "--from", "from_importer",
    help="Add document from a specific importer ({0})".format(
        ", ".join(papis.importer.available_importers())
    ),
    type=(click.Choice(papis.importer.available_importers()), str),
    nargs=2,
    multiple=True,
    default=(),
)
@click.option(
    "-s", "--set",
    help="Update document's information with key value."
         "The value can be a papis format.",
    multiple=True,
    type=(str, str),
)
@click.option(
    "-d", "--delete",
    help="Delete document's key",
    multiple=True,
    type=str,
)
def cli(
        query,
        doc_folder,
        interactive,
        force,
        from_importer,
        auto,
        all,
        set,
        delete
        ):
    """Update a document from a given library"""

    documents = papis.database.get().query(query)
    logger = logging.getLogger('cli:update')
    if not documents:
        logger.warning(papis.strings.no_documents_retrieved_message)

    if doc_folder:
        documents = [papis.document.from_folder(doc_folder)]

    if not all:
        documents = filter(lambda d: d, [papis.pick.pick_doc(documents)])

    for document in documents:
        ctx = papis.importer.Context()
        ctx.data.update(document)

        logger.info(
            'Updating '
            '{c.Back.WHITE}{c.Fore.BLACK}{0}{c.Style.RESET_ALL}'
            .format(papis.document.describe(document), c=colorama)
        )

        if set:
            ctx.data.update(
                {s[0]: papis.utils.format_doc(s[1], document) for s in set}
            )

        if delete:
            for key in delete:
                _delete_key = False
                _confirmation = True
                if interactive:
                    _confirmation = papis.utils.confirm(
                        "Delete {key}?".format(key=key))
                if interactive and _confirmation and not force:
                    _delete_key = True
                elif not _confirmation:
                    _delete_key = False
                else:
                    _delete_key = True
                if _delete_key:
                    try:
                        logger.warning('Deleting {key}'.format(key=key))
                        del document[key]
                    except ValueError:
                        logger.error('Document has no {key}'.format(key=key))
                    else:
                        _update_with_database(document)

    matching_importers = []
    if not from_importer and auto:
        for importer_cls in papis.importer.get_importers():
            try:
                importer = importer_cls.match_data(document)
                importer.fetch()
            except NotImplementedError:
                continue
            except Exception as e:
                logger.exception(e)
            else:
                if importer.ctx:
                    matching_importers.append(importer)

    for _importer_name, _uri in from_importer:
        try:
            _uri = papis.utils.format_doc(_uri, document)
            importer = (papis.importer
                        .get_importer_by_name(_importer_name)(uri=_uri))
            importer.fetch()
            if importer.ctx:
                matching_importers.append(importer)
        except Exception as e:
            logger.exception(e)

    if matching_importers:
        logger.info(
            'There are {0} possible matchings'.format(len(matching_importers)))

        for importer in matching_importers:
            if importer.ctx.data:
                logger.info(
                    'Merging data from importer {0}'.format(importer.name))
                papis.utils.update_doc_from_data_interactively(
                    ctx.data,
                    importer.ctx.data,
                    str(importer))
            if importer.ctx.files:
                logger.info(
                    'Got files {0} from importer {1}'
                    .format(importer.ctx.files, importer.name))
                for f in importer.ctx.files:
                    papis.utils.open_file(f)
                    if papis.utils.confirm("Use this file?"):
                        ctx.files.append(f)

        run(
            document,
            data=ctx.data,
            force=force,)

import ReactMarkdown from "react-markdown";


const TABLE_SEPARATOR =
  /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/;


function splitTableRow(line) {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());
}


function isTableStart(lines, index) {
  if (index + 1 >= lines.length) {
    return false;
  }

  return (
    lines[index].includes("|") &&
    TABLE_SEPARATOR.test(lines[index + 1])
  );
}


function MarkdownCell({ content, header = false }) {
  const Cell = header ? "th" : "td";

  return (
    <Cell>
      <ReactMarkdown>{content}</ReactMarkdown>
    </Cell>
  );
}


function MarkdownTable({ lines }) {
  const headers = splitTableRow(lines[0]);
  const rows = lines.slice(2).map(splitTableRow);

  return (
    <div className="markdown-table-wrap">
      <table className="markdown-table">
        <thead>
          <tr>
            {headers.map((header, index) => (
              <MarkdownCell
                key={`header-${index}`}
                content={header}
                header
              />
            ))}
          </tr>
        </thead>

        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={`row-${rowIndex}`}>
              {headers.map((_, cellIndex) => (
                <MarkdownCell
                  key={`cell-${rowIndex}-${cellIndex}`}
                  content={row[cellIndex] || ""}
                />
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}


function parseBlocks(content) {
  const lines = String(content || "").split("\n");
  const blocks = [];
  let markdownLines = [];

  const flushMarkdown = () => {
    const markdown = markdownLines.join("\n").trim();

    if (markdown) {
      blocks.push({
        type: "markdown",
        content: markdown,
      });
    }

    markdownLines = [];
  };

  let index = 0;

  while (index < lines.length) {
    if (!isTableStart(lines, index)) {
      markdownLines.push(lines[index]);
      index += 1;
      continue;
    }

    flushMarkdown();

    const tableLines = [
      lines[index],
      lines[index + 1],
    ];

    index += 2;

    while (
      index < lines.length &&
      lines[index].trim() &&
      lines[index].includes("|")
    ) {
      tableLines.push(lines[index]);
      index += 1;
    }

    blocks.push({
      type: "table",
      lines: tableLines,
    });
  }

  flushMarkdown();

  return blocks;
}


export default function MarkdownMessage({ content }) {
  const blocks = parseBlocks(content);

  return blocks.map((block, index) => {
    if (block.type === "table") {
      return (
        <MarkdownTable
          key={`table-${index}`}
          lines={block.lines}
        />
      );
    }

    return (
      <ReactMarkdown key={`markdown-${index}`}>
        {block.content}
      </ReactMarkdown>
    );
  });
}

const fs = require("fs");
const path = require("path");
const jsdom = require("jsdom");
const { JSDOM } = jsdom;
const filteredCompanies = require("./filtered_companies.json");

const htmlDir = path.join(__dirname, "company_html");

fs.readdir(htmlDir, (err, files) => {
  if (err) {
    console.error("Error reading HTML directory:", err);
    return;
  }

  const list = [];
  const promises = files
    .filter((file) => file.endsWith(".html"))
    .map((file) => {
      return new Promise((resolve, reject) => {
        const filePath = path.join(htmlDir, file);
        fs.readFile(filePath, "utf-8", (err, data) => {
          if (err) {
            console.error(`Error reading file ${file}:`, err);
            return reject(err);
          }

          const dom = new JSDOM(data);
          const document = dom.window.document;

          const companyIndex = parseInt(
            file.match(/company_(\d+)\.html/)[1],
            10
          );
          const companyDetails = filteredCompanies.find(
            (company) => company.Ranking === companyIndex
          );

          if (!companyDetails) {
            console.error(
              `Company with ranking ${companyIndex} not found in filtered companies.`
            );
            return resolve();
          }

          const details = {
            Ranking: companyDetails.Ranking,
            CompanyName: companyDetails.CompanyName,
            Earnings: [],
            TotalProfit: null,
            MarketCap: null,
            Revenue: [],
          };

          // Get Earnings
          const earningsElement = Array.from(
            document.querySelectorAll("tr")
          ).find((el) =>
            el.textContent.includes("Lợi nhuận sau thuế của công ty mẹ")
          );

          if (earningsElement) {
            earningsElement.childNodes.forEach((node) => {
              if (
                node.nodeName === "TD" &&
                node.textContent &&
                node.textContent.trim() != ""
              ) {
                details.Earnings.push(
                  parseInt(node.textContent.trim().replace(/,/g, ""))
                );
              }
            });

            // remove the first item in the earnings array
            details.Earnings.shift();

            // add total profit
            const totalProfit = details.Earnings.reduce(
              (acc, curr) => acc + curr,
              0
            );
            details["TotalProfit"] = totalProfit;
          }

          // Get Market Cap
          const marketCapElement = Array.from(
            document.querySelectorAll("li")
          ).find((el) => el.textContent.includes("Vốn hóa thị trường"));

          if (marketCapElement) {
            const textValues = [];
            marketCapElement.childNodes.forEach((node) => {
              if (node.textContent && node.textContent.trim() != "") {
                textValues.push(node.textContent.trim().replace(/,/g, ""));
              }
            });

            if (textValues.length > 0) {
              details["MarketCap"] = parseFloat(
                textValues[1].replace(/,/g, "")
              );
            }
          }

          const revenueElement = Array.from(
            document.querySelectorAll("tr")
          ).find((el) => el.textContent.includes("Doanh thu bán hàng và CCDV"));

          if (revenueElement) {
            revenueElement.childNodes.forEach((node) => {
              if (
                node.nodeName === "TD" &&
                node.textContent &&
                node.textContent.trim() != ""
              ) {
                details.Revenue.push(
                  parseInt(node.textContent.trim().replace(/,/g, ""))
                );
              }
            });
          }

          // remove the first item in the revenue array
          details.Revenue.shift();
          // add total revenue
          const totalRevenue = details.Revenue.reduce(
            (acc, curr) => acc + curr,
            0
          );
          details["TotalRevenue"] = totalRevenue;

          list.push(details);
          resolve();
        });
      });
    });

  Promise.all(promises)
    .then(() => {
      const outputFilePath = "company_details.json";
      // sort the list by ranking
      list.sort((a, b) => a.Ranking - b.Ranking);
      fs.writeFile(outputFilePath, JSON.stringify(list, null, 2), (err) => {
        if (err) {
          console.error(`Error writing JSON file ${outputFilePath}:`, err);
        } else {
          console.log(`Company details saved to ${outputFilePath}`);
        }
      });
    })
    .catch((err) => {
      console.error("Error processing files:", err);
    });
});
